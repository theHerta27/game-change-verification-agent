#include "BulletHellGameMode.h"

#include "BulletHellUE.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/LightComponent.h"
#include "Components/SkyLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Dom/JsonObject.h"
#include "Engine/Engine.h"
#include "Engine/DirectionalLight.h"
#include "Engine/SkyLight.h"
#include "Engine/StaticMesh.h"
#include "GameFramework/PlayerController.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformMisc.h"
#include "InputCoreTypes.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"
#include "Misc/App.h"
#include "Misc/CommandLine.h"
#include "Misc/DateTime.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/Parse.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"
#include "UnrealClient.h"

#if PLATFORM_WINDOWS
#include "Windows/AllowWindowsPlatformTypes.h"
#include <bcrypt.h>
#include "Windows/HideWindowsPlatformTypes.h"
#endif

namespace
{
constexpr double FixedStepSeconds = 1.0 / 60.0;
constexpr double WorldScale = 100.0;

FString AbsoluteArgument(const TCHAR* Name)
{
    FString Value;
    if (FParse::Value(FCommandLine::Get(), Name, Value))
    {
        return FPaths::ConvertRelativePathToFull(Value);
    }
    return FString();
}

UMaterialInstanceDynamic* ColoredMaterial(
    UObject* Owner,
    const FLinearColor& Color)
{
    UMaterialInterface* Base = LoadObject<UMaterialInterface>(
        nullptr,
        TEXT("/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial"));
    if (Base == nullptr)
    {
        return nullptr;
    }
    UMaterialInstanceDynamic* Material = UMaterialInstanceDynamic::Create(Base, Owner);
    Material->SetVectorParameterValue(TEXT("Color"), Color);
    return Material;
}

UClass* PresentationClass(const FString& Name)
{
    FString Path;
    if (Name == TEXT("Arena"))
    {
        Path = TEXT("/Game/Presentation/BP_ArenaView.BP_ArenaView_C");
    }
    else if (Name == TEXT("Player"))
    {
        Path = TEXT("/Game/Presentation/BP_PlayerView.BP_PlayerView_C");
    }
    else if (Name == TEXT("Boss"))
    {
        Path = TEXT("/Game/Presentation/BP_BossView.BP_BossView_C");
    }
    else if (Name == TEXT("Projectile Field"))
    {
        Path = TEXT("/Game/Presentation/BP_ProjectileFieldView.BP_ProjectileFieldView_C");
    }
    UClass* Loaded = Path.IsEmpty() ? nullptr : LoadClass<AActor>(nullptr, *Path);
    return Loaded != nullptr ? Loaded : AActor::StaticClass();
}

bool Sha256Hex(const TArray<uint8>& Bytes, FString& OutHex)
{
#if PLATFORM_WINDOWS
    BCRYPT_ALG_HANDLE Algorithm = nullptr;
    BCRYPT_HASH_HANDLE Hash = nullptr;
    DWORD ObjectLength = 0;
    DWORD HashLength = 0;
    DWORD ResultLength = 0;
    TArray<uint8> HashObject;
    TArray<uint8> Digest;

    NTSTATUS Status = BCryptOpenAlgorithmProvider(
        &Algorithm,
        BCRYPT_SHA256_ALGORITHM,
        nullptr,
        0);
    if (Status >= 0)
    {
        Status = BCryptGetProperty(
            Algorithm,
            BCRYPT_OBJECT_LENGTH,
            reinterpret_cast<PUCHAR>(&ObjectLength),
            sizeof(ObjectLength),
            &ResultLength,
            0);
    }
    if (Status >= 0)
    {
        Status = BCryptGetProperty(
            Algorithm,
            BCRYPT_HASH_LENGTH,
            reinterpret_cast<PUCHAR>(&HashLength),
            sizeof(HashLength),
            &ResultLength,
            0);
    }
    if (Status >= 0)
    {
        HashObject.SetNumUninitialized(ObjectLength);
        Digest.SetNumUninitialized(HashLength);
        Status = BCryptCreateHash(
            Algorithm,
            &Hash,
            HashObject.GetData(),
            HashObject.Num(),
            nullptr,
            0,
            0);
    }
    if (Status >= 0)
    {
        Status = BCryptHashData(
            Hash,
            const_cast<PUCHAR>(Bytes.GetData()),
            Bytes.Num(),
            0);
    }
    if (Status >= 0)
    {
        Status = BCryptFinishHash(Hash, Digest.GetData(), Digest.Num(), 0);
    }

    if (Hash != nullptr)
    {
        BCryptDestroyHash(Hash);
    }
    if (Algorithm != nullptr)
    {
        BCryptCloseAlgorithmProvider(Algorithm, 0);
    }
    if (Status < 0)
    {
        return false;
    }

    OutHex.Reset(Digest.Num() * 2);
    for (const uint8 Byte : Digest)
    {
        OutHex += FString::Printf(TEXT("%02x"), Byte);
    }
    return true;
#else
    return false;
#endif
}
}

ABulletHellGameMode::ABulletHellGameMode()
{
    PrimaryActorTick.bCanEverTick = true;
    DefaultPawnClass = nullptr;
}

void ABulletHellGameMode::BeginPlay()
{
    Super::BeginPlay();
    if (GEngine != nullptr)
    {
        GEngine->SetMaxFPS(60.0f);
    }

    FString Error;
    if (!ReadCommandLine(Error))
    {
        FailAndExit(TEXT("command_line_error"), Error, 2);
        return;
    }
    if (!ValidateConfigHash(Error))
    {
        FailAndExit(TEXT("config_hash_mismatch"), Error, 3);
        return;
    }
    if (!FBulletHellContract::LoadStrict(ConfigPath, Contract, Error))
    {
        FailAndExit(TEXT("config_validation_error"), Error, 4);
        return;
    }

    Simulation.Initialize(Contract, Seed);
    PlayerPosition = FVector2D(Contract.PlayerStartX, Contract.PlayerStartZ);
    CreatePresentation();
    bInitialized = true;
    UE_LOG(
        LogBulletHellUE,
        Display,
        TEXT("Bullet Hell run initialized: run=%s variant=%s seed=%d config=%s"),
        *RunId,
        *Variant,
        Seed,
        *ConfigPath);
}

void ABulletHellGameMode::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if (!bInitialized)
    {
        return;
    }
    if (bFinishing)
    {
        if (!bTelemetryWritten && CapturesExist())
        {
            FinishRun();
        }
        else if (FPlatformTime::Seconds() - FinishRequestedAt > 3.0)
        {
            FailAndExit(
                TEXT("screenshot_error"),
                TEXT("One or more scheduled screenshots were not written within 3 seconds."),
                5);
        }
        return;
    }

    RecordFrame(DeltaSeconds);
    if (!bAutomated)
    {
        UpdateManualPlayer(DeltaSeconds);
    }

    FixedAccumulator += FMath::Min(static_cast<double>(DeltaSeconds), 0.25);
    while (FixedAccumulator >= FixedStepSeconds && !Simulation.IsFinished())
    {
        if (bAutomated)
        {
            PlayerPosition = Simulation.AutomaticPlayerPosition();
        }
        Simulation.Step(FixedStepSeconds, PlayerPosition);
        FixedAccumulator -= FixedStepSeconds;
    }

    UpdatePresentation();
    RequestScheduledCaptures();
    if (Simulation.IsFinished())
    {
        if (bAutomated)
        {
            bFinishing = true;
            FinishRequestedAt = FPlatformTime::Seconds();
            if (CapturesExist())
            {
                FinishRun();
            }
        }
        else if (!bTelemetryWritten)
        {
            FinishRun();
        }
    }
}

bool ABulletHellGameMode::ReadCommandLine(FString& OutError)
{
    ConfigPath = AbsoluteArgument(TEXT("ConfigInput="));
    TelemetryPath = AbsoluteArgument(TEXT("TelemetryOutput="));
    ScreenshotDirectory = AbsoluteArgument(TEXT("ScreenshotDir="));
    FParse::Value(FCommandLine::Get(), TEXT("ConfigHash="), ExpectedConfigHash);
    FParse::Value(FCommandLine::Get(), TEXT("ConfigFileHash="), ExpectedConfigFileHash);
    FParse::Value(FCommandLine::Get(), TEXT("RunId="), RunId);
    FParse::Value(FCommandLine::Get(), TEXT("Variant="), Variant);
    FParse::Value(FCommandLine::Get(), TEXT("Seed="), Seed);
    bAutomated = FParse::Param(FCommandLine::Get(), TEXT("Automated"));

    if (ConfigPath.IsEmpty() || TelemetryPath.IsEmpty())
    {
        OutError = TEXT("-ConfigInput and -TelemetryOutput are required.");
        return false;
    }
    if (ExpectedConfigHash.IsEmpty() || ExpectedConfigFileHash.IsEmpty())
    {
        OutError = TEXT("-ConfigHash and -ConfigFileHash are required.");
        return false;
    }
    if (RunId.IsEmpty()
        || (Variant != TEXT("baseline") && !Variant.StartsWith(TEXT("candidate"))))
    {
        OutError = TEXT("-RunId and -Variant=baseline|candidate* are required.");
        return false;
    }
    if (bAutomated && ScreenshotDirectory.IsEmpty())
    {
        OutError = TEXT("-ScreenshotDir is required for automated runs.");
        return false;
    }
    CaptureTimes = {10, 20, 30};
    IFileManager::Get().MakeDirectory(*FPaths::GetPath(TelemetryPath), true);
    if (!ScreenshotDirectory.IsEmpty())
    {
        IFileManager::Get().MakeDirectory(*ScreenshotDirectory, true);
    }
    return true;
}

bool ABulletHellGameMode::ValidateConfigHash(FString& OutError) const
{
    TArray<uint8> Bytes;
    if (!FFileHelper::LoadFileToArray(Bytes, *ConfigPath))
    {
        OutError = FString::Printf(TEXT("ConfigInput was not readable: %s"), *ConfigPath);
        return false;
    }
    FString Actual;
    if (!Sha256Hex(Bytes, Actual))
    {
        OutError = TEXT("UE could not calculate ConfigInput SHA256.");
        return false;
    }
    if (!Actual.Equals(ExpectedConfigFileHash, ESearchCase::IgnoreCase))
    {
        OutError = FString::Printf(
            TEXT("ConfigInput SHA256 mismatch: expected %s, actual %s."),
            *ExpectedConfigFileHash,
            *Actual);
        return false;
    }
    return true;
}

void ABulletHellGameMode::CreatePresentation()
{
    UWorld* World = GetWorld();
    ADirectionalLight* DirectionalLight = World->SpawnActor<ADirectionalLight>(
        FVector(0.0, 0.0, 1800.0),
        FRotator(-55.0, -35.0, 0.0));
    DirectionalLight->GetLightComponent()->SetIntensity(8.0f);
    DirectionalLight->GetLightComponent()->SetLightColor(FLinearColor(1.0f, 0.92f, 0.82f));

    ASkyLight* SkyLight = World->SpawnActor<ASkyLight>();
    SkyLight->GetLightComponent()->SetIntensity(1.6f);
    SkyLight->GetLightComponent()->SetLightColor(FLinearColor(0.3f, 0.48f, 0.8f));
    SkyLight->GetLightComponent()->SetMobility(EComponentMobility::Movable);

    CreateMeshActor(
        TEXT("Arena"),
        TEXT("/Engine/BasicShapes/Cube.Cube"),
        FVector(0.0, 0.0, -30.0),
        FVector(Contract.ArenaWidth, Contract.ArenaHeight, 0.2),
        FLinearColor(0.025f, 0.07f, 0.12f));

    PlayerActor = CreateMeshActor(
        TEXT("Player"),
        TEXT("/Engine/BasicShapes/Cone.Cone"),
        FVector(PlayerPosition.X * WorldScale, PlayerPosition.Y * WorldScale, 60.0),
        FVector(0.55, 0.55, 0.75),
        FLinearColor(0.1f, 0.8f, 1.0f));
    BossActor = CreateMeshActor(
        TEXT("Boss"),
        TEXT("/Engine/BasicShapes/Cylinder.Cylinder"),
        FVector(Contract.BossPositionX * WorldScale, Contract.BossPositionZ * WorldScale, 80.0),
        FVector(1.25, 1.25, 0.7),
        FLinearColor(0.95f, 0.08f, 0.25f));

    AActor* BulletField = World->SpawnActor<AActor>(PresentationClass(TEXT("Projectile Field")));
#if WITH_EDITOR
    BulletField->SetActorLabel(TEXT("Projectile Field"));
#endif
    BulletInstances = NewObject<UInstancedStaticMeshComponent>(BulletField);
    BulletField->SetRootComponent(BulletInstances);
    BulletField->AddInstanceComponent(BulletInstances);
    BulletInstances->SetStaticMesh(LoadObject<UStaticMesh>(
        nullptr,
        TEXT("/Engine/BasicShapes/Sphere.Sphere")));
    if (UMaterialInstanceDynamic* Material =
        ColoredMaterial(BulletInstances, FLinearColor(1.0f, 0.62f, 0.05f)))
    {
        BulletInstances->SetMaterial(0, Material);
    }
    BulletInstances->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    BulletInstances->RegisterComponent();

    ACameraActor* Camera = World->SpawnActor<ACameraActor>(
        FVector(0.0, 0.0, 3000.0),
        FRotator(-90.0, -90.0, 0.0));
    Camera->GetCameraComponent()->SetProjectionMode(ECameraProjectionMode::Orthographic);
    Camera->GetCameraComponent()->SetOrthoWidth(Contract.ArenaHeight * WorldScale * 1.8);
    Camera->GetCameraComponent()->SetAspectRatio(16.0f / 9.0f);
    Camera->GetCameraComponent()->bConstrainAspectRatio = true;
    Camera->GetCameraComponent()->PostProcessSettings.AutoExposureMethod =
        EAutoExposureMethod::AEM_Manual;
    Camera->GetCameraComponent()->PostProcessSettings.AutoExposureBias = 0.0f;
    if (APlayerController* Controller = World->GetFirstPlayerController())
    {
        Controller->SetViewTarget(Camera);
    }
}

AActor* ABulletHellGameMode::CreateMeshActor(
    const FString& Name,
    const FString& MeshPath,
    const FVector& Location,
    const FVector& Scale,
    const FLinearColor& Color)
{
    AActor* Actor = GetWorld()->SpawnActor<AActor>(PresentationClass(Name));
#if WITH_EDITOR
    Actor->SetActorLabel(*Name);
#endif
    UStaticMeshComponent* Mesh = NewObject<UStaticMeshComponent>(Actor);
    Actor->SetRootComponent(Mesh);
    Actor->AddInstanceComponent(Mesh);
    Mesh->SetStaticMesh(LoadObject<UStaticMesh>(nullptr, *MeshPath));
    if (UMaterialInstanceDynamic* Material = ColoredMaterial(Mesh, Color))
    {
        Mesh->SetMaterial(0, Material);
    }
    Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Mesh->RegisterComponent();
    Actor->SetActorLocation(Location);
    Actor->SetActorScale3D(Scale);
    return Actor;
}

void ABulletHellGameMode::UpdateManualPlayer(double DeltaSeconds)
{
    APlayerController* Controller = GetWorld()->GetFirstPlayerController();
    if (Controller == nullptr)
    {
        return;
    }
    FVector2D Direction(
        (Controller->IsInputKeyDown(EKeys::D) ? 1.0 : 0.0)
            - (Controller->IsInputKeyDown(EKeys::A) ? 1.0 : 0.0),
        (Controller->IsInputKeyDown(EKeys::W) ? 1.0 : 0.0)
            - (Controller->IsInputKeyDown(EKeys::S) ? 1.0 : 0.0));
    if (!Direction.IsNearlyZero())
    {
        Direction.Normalize();
        const bool bFocus = Controller->IsInputKeyDown(EKeys::LeftShift)
            || Controller->IsInputKeyDown(EKeys::RightShift);
        const double Speed = Contract.PlayerMoveSpeed
            * (bFocus ? Contract.FocusSpeedMultiplier : 1.0);
        PlayerPosition += Direction * Speed * DeltaSeconds;
    }
    PlayerPosition.X = FMath::Clamp(
        PlayerPosition.X,
        -Contract.ArenaWidth * 0.5 + 0.4,
        Contract.ArenaWidth * 0.5 - 0.4);
    PlayerPosition.Y = FMath::Clamp(
        PlayerPosition.Y,
        -Contract.ArenaHeight * 0.5 + 0.4,
        Contract.ArenaHeight * 0.5 - 0.4);
}

void ABulletHellGameMode::UpdatePresentation()
{
    if (PlayerActor != nullptr)
    {
        PlayerActor->SetActorLocation(
            FVector(PlayerPosition.X * WorldScale, PlayerPosition.Y * WorldScale, 60.0));
    }
    if (BossActor != nullptr)
    {
        BossActor->SetActorRotation(
            FRotator(0.0, Simulation.GetElapsedSeconds() * 28.0, 0.0));
    }
    if (BulletInstances != nullptr)
    {
        BulletInstances->ClearInstances();
        for (const FBulletHellProjectile& Projectile : Simulation.GetProjectiles())
        {
            BulletInstances->AddInstance(FTransform(
                FRotator::ZeroRotator,
                FVector(Projectile.Position.X * WorldScale, Projectile.Position.Y * WorldScale, 55.0),
                FVector(0.24, 0.24, 0.24)));
        }
    }

    if (GEngine != nullptr)
    {
        GEngine->AddOnScreenDebugMessage(
            1,
            0.0f,
            FColor::White,
            FString::Printf(
                TEXT("Game Change Verification Agent | UE 5.8.1 | %s"),
                *Variant));
        GEngine->AddOnScreenDebugMessage(
            2,
            0.0f,
            FColor::Cyan,
            FString::Printf(
                TEXT("%.1fs | %s / %s | bullets %d | hits %d"),
                Simulation.GetElapsedSeconds(),
                *Simulation.GetCurrentPhase().PhaseId,
                *Simulation.GetCurrentPhase().Pattern.Type,
                Simulation.GetProjectiles().Num(),
                Simulation.GetPlayerHits()));
        GEngine->AddOnScreenDebugMessage(
            3,
            0.0f,
            FColor::Yellow,
            FString::Printf(
                TEXT("Boss %.0f%% | Player %d/%d | seed %d"),
                Simulation.GetBossHealthRatio() * 100.0,
                Simulation.GetPlayerHealth(),
                Contract.PlayerMaxHealth,
                Seed));
    }
}

void ABulletHellGameMode::RecordFrame(double DeltaSeconds)
{
    if (Simulation.GetElapsedSeconds() >= 2.0 && DeltaSeconds > 0.0)
    {
        FrameTimes.Add(DeltaSeconds);
    }
}

void ABulletHellGameMode::RequestScheduledCaptures()
{
    if (!bAutomated || bFinishing || ScreenshotDirectory.IsEmpty())
    {
        return;
    }
    while (Captures.Num() < CaptureTimes.Num()
        && Simulation.GetElapsedSeconds() >= CaptureTimes[Captures.Num()])
    {
        const int32 CaptureTime = CaptureTimes[Captures.Num()];
        const FString FileName = FString::Printf(TEXT("capture_%02ds.png"), CaptureTime);
        const FString FilePath = FPaths::Combine(ScreenshotDirectory, FileName);
        FScreenshotRequest::RequestScreenshot(FilePath, false, false);

        FBulletHellCaptureRecord Record;
        Record.TimeSeconds = CaptureTime;
        Record.PhaseId = Simulation.GetCurrentPhase().PhaseId;
        Record.PhaseName = Simulation.GetCurrentPhase().DisplayName;
        Record.PatternType = Simulation.GetCurrentPhase().Pattern.Type;
        Record.FileName = FileName;
        Captures.Add(MoveTemp(Record));
    }
}

void ABulletHellGameMode::FinishRun()
{
    const bool bCompleted = Simulation.DidCompleteScenario();
    WriteCaptureManifest();
    WriteTelemetry(bCompleted ? TEXT("completed") : TEXT("failed"), true, 0);
    bTelemetryWritten = true;
    if (bAutomated)
    {
        FPlatformMisc::RequestExitWithStatus(
            false,
            bCompleted ? 0 : 1,
            TEXT("ABulletHellGameMode::FinishRun"));
    }
}

void ABulletHellGameMode::WriteTelemetry(
    const FString& Status,
    bool bCompleted,
    int32 RuntimeErrorCount,
    const FString& ErrorType,
    const FString& ErrorMessage)
{
    TSharedRef<FJsonObject> Root = MakeShared<FJsonObject>();
    Root->SetStringField(TEXT("contract_version"), TEXT("1.0"));
    Root->SetStringField(TEXT("bullet_hell_contract_version"), TEXT("1.0"));
    Root->SetStringField(TEXT("engine_name"), TEXT("unreal"));
    Root->SetStringField(TEXT("engine_version"), EngineVersionString());
    Root->SetStringField(TEXT("build_id"), BuildIdString());
    Root->SetStringField(TEXT("run_id"), RunId);
    Root->SetStringField(TEXT("config_hash"), ExpectedConfigHash);
    Root->SetNumberField(TEXT("seed"), Seed);
    Root->SetStringField(TEXT("scenario_id"), Contract.ScenarioId);
    Root->SetStringField(TEXT("status"), Status);
    Root->SetStringField(TEXT("run_mode"), bAutomated ? TEXT("automated") : TEXT("manual"));
    Root->SetNumberField(TEXT("duration_seconds"), Simulation.GetElapsedSeconds());
    Root->SetNumberField(TEXT("total_bullets_spawned"), Simulation.GetTotalBulletsSpawned());
    Root->SetNumberField(TEXT("peak_alive_bullets"), Simulation.GetPeakAliveBullets());
    Root->SetNumberField(
        TEXT("bullets_per_second"),
        Simulation.GetElapsedSeconds() > 0.0
            ? Simulation.GetTotalBulletsSpawned() / Simulation.GetElapsedSeconds()
            : 0.0);
    Root->SetNumberField(TEXT("player_hits"), Simulation.GetPlayerHits());
    Root->SetNumberField(TEXT("player_survival_seconds"), Simulation.GetElapsedSeconds());

    double AverageFps = 0.0;
    double LowPercentileFps = 0.0;
    double MinimumFps = 0.0;
    if (!FrameTimes.IsEmpty())
    {
        double Total = 0.0;
        TArray<double> Ordered = FrameTimes;
        Ordered.Sort();
        for (const double FrameTime : Ordered)
        {
            Total += FrameTime;
        }
        AverageFps = 1.0 / (Total / Ordered.Num());
        const int32 PercentileIndex = FMath::Min(
            Ordered.Num() - 1,
            FMath::FloorToInt(Ordered.Num() * 0.95));
        LowPercentileFps = 1.0 / Ordered[PercentileIndex];
        MinimumFps = 1.0 / Ordered.Last();
    }
    Root->SetNumberField(TEXT("average_fps"), AverageFps);
    Root->SetNumberField(TEXT("low_percentile_fps"), LowPercentileFps);
    Root->SetNumberField(TEXT("minimum_fps"), MinimumFps);
    Root->SetNumberField(TEXT("runtime_error_count"), RuntimeErrorCount);
    Root->SetNumberField(TEXT("exception_log_count"), RuntimeErrorCount);
    Root->SetNumberField(TEXT("frame_count"), FrameTimes.Num());
    Root->SetBoolField(TEXT("completed"), bCompleted);
    Root->SetStringField(TEXT("exported_at_utc"), FDateTime::UtcNow().ToIso8601());
    Root->SetStringField(
        TEXT("screenshot_status"),
        bAutomated ? (CapturesExist() ? TEXT("completed") : TEXT("missing")) : TEXT("not_requested"));
    if (!ErrorType.IsEmpty())
    {
        Root->SetStringField(TEXT("error_type"), ErrorType);
        Root->SetStringField(TEXT("error_message"), ErrorMessage);
    }

    TArray<TSharedPtr<FJsonValue>> PhaseValues;
    for (const FBulletHellPhaseTelemetry& Phase : Simulation.FinalizePhases())
    {
        TSharedRef<FJsonObject> PhaseObject = MakeShared<FJsonObject>();
        PhaseObject->SetStringField(TEXT("phase_id"), Phase.PhaseId);
        PhaseObject->SetStringField(TEXT("pattern_type"), Phase.PatternType);
        PhaseObject->SetNumberField(TEXT("started_at_seconds"), Phase.StartedAtSeconds);
        PhaseObject->SetNumberField(TEXT("duration_seconds"), Phase.DurationSeconds);
        PhaseObject->SetNumberField(TEXT("bullets_spawned"), Phase.BulletsSpawned);
        PhaseObject->SetNumberField(TEXT("player_hits"), Phase.PlayerHits);
        PhaseObject->SetNumberField(TEXT("peak_alive_bullets"), Phase.PeakAliveBullets);
        PhaseValues.Add(MakeShared<FJsonValueObject>(PhaseObject));
    }
    Root->SetArrayField(TEXT("phase_results"), PhaseValues);

    FString Json;
    const TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&Json);
    FJsonSerializer::Serialize(Root, Writer);
    IFileManager::Get().MakeDirectory(*FPaths::GetPath(TelemetryPath), true);
    FFileHelper::SaveStringToFile(Json, *TelemetryPath, FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
}

void ABulletHellGameMode::WriteCaptureManifest() const
{
    if (!bAutomated)
    {
        return;
    }
    TSharedRef<FJsonObject> Root = MakeShared<FJsonObject>();
    Root->SetStringField(TEXT("engine_name"), TEXT("unreal"));
    Root->SetStringField(TEXT("engine_version"), EngineVersionString());
    Root->SetStringField(TEXT("run_id"), RunId);
    Root->SetStringField(TEXT("variant"), Variant);
    Root->SetStringField(TEXT("config_hash"), ExpectedConfigHash);
    Root->SetNumberField(TEXT("random_seed"), Seed);
    Root->SetStringField(TEXT("run_mode"), TEXT("automated"));
    Root->SetBoolField(TEXT("fixed_trajectory"), true);
    Root->SetNumberField(TEXT("duration_seconds"), Contract.DurationSeconds);

    TArray<TSharedPtr<FJsonValue>> Values;
    for (const FBulletHellCaptureRecord& Capture : Captures)
    {
        TSharedRef<FJsonObject> Object = MakeShared<FJsonObject>();
        Object->SetNumberField(TEXT("time_seconds"), Capture.TimeSeconds);
        Object->SetStringField(TEXT("phase_id"), Capture.PhaseId);
        Object->SetStringField(TEXT("phase_name"), Capture.PhaseName);
        Object->SetStringField(TEXT("pattern_type"), Capture.PatternType);
        Object->SetStringField(TEXT("file_name"), Capture.FileName);
        Values.Add(MakeShared<FJsonValueObject>(Object));
    }
    Root->SetArrayField(TEXT("captures"), Values);

    FString Json;
    const TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&Json);
    FJsonSerializer::Serialize(Root, Writer);
    const FString Path = FPaths::Combine(ScreenshotDirectory, TEXT("capture_manifest.json"));
    FFileHelper::SaveStringToFile(Json, *Path, FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
}

void ABulletHellGameMode::FailAndExit(
    const FString& ErrorType,
    const FString& ErrorMessage,
    uint8 ExitCode)
{
    UE_LOG(LogBulletHellUE, Error, TEXT("%s: %s"), *ErrorType, *ErrorMessage);
    if (!TelemetryPath.IsEmpty())
    {
        WriteTelemetry(ErrorType, false, 1, ErrorType, ErrorMessage);
    }
    bTelemetryWritten = true;
    FPlatformMisc::RequestExitWithStatus(
        false,
        ExitCode,
        TEXT("ABulletHellGameMode::FailAndExit"));
}

bool ABulletHellGameMode::CapturesExist() const
{
    if (!bAutomated || Captures.Num() != CaptureTimes.Num())
    {
        return !bAutomated;
    }
    for (const FBulletHellCaptureRecord& Capture : Captures)
    {
        if (!FPaths::FileExists(FPaths::Combine(ScreenshotDirectory, Capture.FileName)))
        {
            return false;
        }
    }
    return true;
}

FString ABulletHellGameMode::EngineVersionString() const
{
    return FEngineVersion::Current().ToString();
}

FString ABulletHellGameMode::BuildIdString() const
{
    return FString::Printf(
        TEXT("%d-%s"),
        FEngineVersion::Current().GetChangelist(),
        LexToString(FApp::GetBuildConfiguration()));
}
