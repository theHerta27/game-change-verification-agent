#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "BulletHellContract.h"
#include "BulletHellSimulation.h"
#include "BulletHellGameMode.generated.h"

class ACameraActor;
class UInstancedStaticMeshComponent;
class UStaticMeshComponent;

USTRUCT()
struct FBulletHellCaptureRecord
{
    GENERATED_BODY()

    double TimeSeconds = 0.0;
    FString PhaseId;
    FString PhaseName;
    FString PatternType;
    FString FileName;
};

UCLASS()
class BULLETHELLUE_API ABulletHellGameMode : public AGameModeBase
{
    GENERATED_BODY()

public:
    ABulletHellGameMode();

    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;

private:
    bool ReadCommandLine(FString& OutError);
    bool ValidateConfigHash(FString& OutError) const;
    void CreatePresentation();
    AActor* CreateMeshActor(
        const FString& Name,
        const FString& MeshPath,
        const FVector& Location,
        const FVector& Scale,
        const FLinearColor& Color);
    void UpdateManualPlayer(double DeltaSeconds);
    void UpdatePresentation();
    void RecordFrame(double DeltaSeconds);
    void RequestScheduledCaptures();
    void FinishRun();
    void WriteTelemetry(
        const FString& Status,
        bool bCompleted,
        int32 RuntimeErrorCount,
        const FString& ErrorType = FString(),
        const FString& ErrorMessage = FString());
    void WriteCaptureManifest() const;
    void FailAndExit(const FString& ErrorType, const FString& ErrorMessage, uint8 ExitCode);
    bool CapturesExist() const;
    FString EngineVersionString() const;
    FString BuildIdString() const;

    FBulletHellContract Contract;
    FBulletHellSimulation Simulation;
    FVector2D PlayerPosition = FVector2D::ZeroVector;
    TArray<double> FrameTimes;
    TArray<FBulletHellCaptureRecord> Captures;
    TArray<int32> CaptureTimes;

    FString ConfigPath;
    FString TelemetryPath;
    FString ScreenshotDirectory;
    FString ExpectedConfigHash;
    FString ExpectedConfigFileHash;
    FString RunId;
    FString Variant;
    int32 Seed = 20260727;
    bool bAutomated = false;
    bool bInitialized = false;
    bool bFinishing = false;
    bool bTelemetryWritten = false;
    double FixedAccumulator = 0.0;
    double FinishRequestedAt = 0.0;

    TObjectPtr<AActor> PlayerActor;
    TObjectPtr<AActor> BossActor;
    TObjectPtr<UInstancedStaticMeshComponent> BulletInstances;
};
