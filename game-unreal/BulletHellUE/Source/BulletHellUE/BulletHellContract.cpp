#include "BulletHellContract.h"

#include "Dom/JsonObject.h"
#include "HAL/FileManager.h"
#include "Misc/FileHelper.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

namespace
{
bool ValidateKeys(
    const TSharedPtr<FJsonObject>& Object,
    const TSet<FString>& Allowed,
    const FString& Path,
    FString& OutError)
{
    for (const TPair<FString, TSharedPtr<FJsonValue>>& Field : Object->Values)
    {
        if (!Allowed.Contains(Field.Key))
        {
            OutError = FString::Printf(TEXT("%s contains unsupported field '%s'."), *Path, *Field.Key);
            return false;
        }
    }
    return true;
}

bool RequiredObject(
    const TSharedPtr<FJsonObject>& Parent,
    const TCHAR* Name,
    const FString& Path,
    TSharedPtr<FJsonObject>& OutObject,
    FString& OutError)
{
    const TSharedPtr<FJsonObject>* Value = nullptr;
    if (!Parent->TryGetObjectField(Name, Value) || Value == nullptr || !Value->IsValid())
    {
        OutError = FString::Printf(TEXT("%s.%s expected object."), *Path, Name);
        return false;
    }
    OutObject = *Value;
    return true;
}

bool RequiredString(
    const TSharedPtr<FJsonObject>& Object,
    const TCHAR* Name,
    const FString& Path,
    FString& OutValue,
    FString& OutError)
{
    if (!Object->TryGetStringField(Name, OutValue) || OutValue.IsEmpty())
    {
        OutError = FString::Printf(TEXT("%s.%s expected non-empty string."), *Path, Name);
        return false;
    }
    return true;
}

template <typename T>
bool RequiredNumber(
    const TSharedPtr<FJsonObject>& Object,
    const TCHAR* Name,
    const FString& Path,
    T& OutValue,
    FString& OutError)
{
    if (!Object->TryGetNumberField(Name, OutValue))
    {
        OutError = FString::Printf(TEXT("%s.%s expected number."), *Path, Name);
        return false;
    }
    return true;
}

bool RequiredBool(
    const TSharedPtr<FJsonObject>& Object,
    const TCHAR* Name,
    const FString& Path,
    bool& OutValue,
    FString& OutError)
{
    if (!Object->TryGetBoolField(Name, OutValue))
    {
        OutError = FString::Printf(TEXT("%s.%s expected boolean."), *Path, Name);
        return false;
    }
    return true;
}

bool ParsePattern(
    const TSharedPtr<FJsonObject>& Object,
    const FString& Path,
    FBulletHellPattern& OutPattern,
    FString& OutError)
{
    static const TSet<FString> Keys = {
        TEXT("type"),
        TEXT("bullets_per_wave"),
        TEXT("wave_interval_ms"),
        TEXT("bullet_speed"),
        TEXT("bullet_lifetime_seconds"),
        TEXT("rotation_per_wave_deg"),
        TEXT("spread_angle_deg"),
        TEXT("layer_count"),
        TEXT("bidirectional")
    };
    if (!ValidateKeys(Object, Keys, Path, OutError)
        || !RequiredString(Object, TEXT("type"), Path, OutPattern.Type, OutError)
        || !RequiredNumber(Object, TEXT("bullets_per_wave"), Path, OutPattern.BulletsPerWave, OutError)
        || !RequiredNumber(Object, TEXT("wave_interval_ms"), Path, OutPattern.WaveIntervalMs, OutError)
        || !RequiredNumber(Object, TEXT("bullet_speed"), Path, OutPattern.BulletSpeed, OutError)
        || !RequiredNumber(Object, TEXT("bullet_lifetime_seconds"), Path, OutPattern.BulletLifetimeSeconds, OutError)
        || !RequiredNumber(Object, TEXT("rotation_per_wave_deg"), Path, OutPattern.RotationPerWaveDeg, OutError)
        || !RequiredNumber(Object, TEXT("spread_angle_deg"), Path, OutPattern.SpreadAngleDeg, OutError)
        || !RequiredNumber(Object, TEXT("layer_count"), Path, OutPattern.LayerCount, OutError)
        || !RequiredBool(Object, TEXT("bidirectional"), Path, OutPattern.Bidirectional, OutError))
    {
        return false;
    }

    static const TSet<FString> Supported = {
        TEXT("ring"), TEXT("aimed_fan"), TEXT("spiral"), TEXT("petal")
    };
    if (!Supported.Contains(OutPattern.Type))
    {
        OutError = FString::Printf(TEXT("%s.type '%s' is an unsupported capability."), *Path, *OutPattern.Type);
        return false;
    }
    if (OutPattern.BulletsPerWave < 1 || OutPattern.BulletsPerWave > 64)
    {
        OutError = FString::Printf(TEXT("%s.bullets_per_wave is outside 1..64."), *Path);
        return false;
    }
    if (OutPattern.WaveIntervalMs < 100 || OutPattern.WaveIntervalMs > 5000)
    {
        OutError = FString::Printf(TEXT("%s.wave_interval_ms is outside 100..5000."), *Path);
        return false;
    }
    if (OutPattern.BulletSpeed < 0.5 || OutPattern.BulletSpeed > 12.0)
    {
        OutError = FString::Printf(TEXT("%s.bullet_speed is outside 0.5..12."), *Path);
        return false;
    }
    if (OutPattern.BulletLifetimeSeconds < 0.5 || OutPattern.BulletLifetimeSeconds > 12.0)
    {
        OutError = FString::Printf(TEXT("%s.bullet_lifetime_seconds is outside 0.5..12."), *Path);
        return false;
    }
    if (OutPattern.LayerCount < 1 || OutPattern.LayerCount > 4)
    {
        OutError = FString::Printf(TEXT("%s.layer_count is outside 1..4."), *Path);
        return false;
    }
    if (OutPattern.Type == TEXT("petal") && OutPattern.LayerCount < 2)
    {
        OutError = FString::Printf(TEXT("%s.petal requires at least two layers."), *Path);
        return false;
    }
    return true;
}
}

bool FBulletHellContract::LoadStrict(
    const FString& FilePath,
    FBulletHellContract& OutContract,
    FString& OutError)
{
    FString JsonText;
    if (!FPaths::FileExists(FilePath) || !FFileHelper::LoadFileToString(JsonText, *FilePath))
    {
        OutError = FString::Printf(TEXT("ConfigInput was not readable: %s"), *FilePath);
        return false;
    }

    TSharedPtr<FJsonObject> Root;
    const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(JsonText);
    if (!FJsonSerializer::Deserialize(Reader, Root) || !Root.IsValid())
    {
        OutError = TEXT("ConfigInput is not valid JSON.");
        return false;
    }

    static const TSet<FString> RootKeys = {
        TEXT("bullet_hell_contract_version"),
        TEXT("source"),
        TEXT("scenario"),
        TEXT("player"),
        TEXT("boss"),
        TEXT("phases"),
        TEXT("constraints"),
        TEXT("runtime_targets")
    };
    if (!ValidateKeys(Root, RootKeys, TEXT("root"), OutError)
        || !RequiredString(
            Root,
            TEXT("bullet_hell_contract_version"),
            TEXT("root"),
            OutContract.ContractVersion,
            OutError))
    {
        return false;
    }
    if (OutContract.ContractVersion != TEXT("1.0"))
    {
        OutError = TEXT("bullet_hell_contract_version must be 1.0.");
        return false;
    }

    TSharedPtr<FJsonObject> Scenario;
    TSharedPtr<FJsonObject> Player;
    TSharedPtr<FJsonObject> Boss;
    TSharedPtr<FJsonObject> Constraints;
    TSharedPtr<FJsonObject> RuntimeTargets;
    if (!RequiredObject(Root, TEXT("scenario"), TEXT("root"), Scenario, OutError)
        || !RequiredObject(Root, TEXT("player"), TEXT("root"), Player, OutError)
        || !RequiredObject(Root, TEXT("boss"), TEXT("root"), Boss, OutError)
        || !RequiredObject(Root, TEXT("constraints"), TEXT("root"), Constraints, OutError)
        || !RequiredObject(Root, TEXT("runtime_targets"), TEXT("root"), RuntimeTargets, OutError))
    {
        return false;
    }

    static const TSet<FString> ScenarioKeys = {
        TEXT("scenario_id"), TEXT("display_name"), TEXT("duration_seconds"),
        TEXT("arena_width"), TEXT("arena_height")
    };
    if (!ValidateKeys(Scenario, ScenarioKeys, TEXT("scenario"), OutError)
        || !RequiredString(Scenario, TEXT("scenario_id"), TEXT("scenario"), OutContract.ScenarioId, OutError)
        || !RequiredString(Scenario, TEXT("display_name"), TEXT("scenario"), OutContract.ScenarioName, OutError)
        || !RequiredNumber(Scenario, TEXT("duration_seconds"), TEXT("scenario"), OutContract.DurationSeconds, OutError)
        || !RequiredNumber(Scenario, TEXT("arena_width"), TEXT("scenario"), OutContract.ArenaWidth, OutError)
        || !RequiredNumber(Scenario, TEXT("arena_height"), TEXT("scenario"), OutContract.ArenaHeight, OutError))
    {
        return false;
    }

    static const TSet<FString> PlayerKeys = {
        TEXT("max_health"), TEXT("move_speed"), TEXT("focus_speed_multiplier"), TEXT("hit_radius"),
        TEXT("start_x"), TEXT("start_z"), TEXT("auto_fire_damage"), TEXT("auto_fire_interval_seconds")
    };
    if (!ValidateKeys(Player, PlayerKeys, TEXT("player"), OutError)
        || !RequiredNumber(Player, TEXT("max_health"), TEXT("player"), OutContract.PlayerMaxHealth, OutError)
        || !RequiredNumber(Player, TEXT("move_speed"), TEXT("player"), OutContract.PlayerMoveSpeed, OutError)
        || !RequiredNumber(Player, TEXT("focus_speed_multiplier"), TEXT("player"), OutContract.FocusSpeedMultiplier, OutError)
        || !RequiredNumber(Player, TEXT("hit_radius"), TEXT("player"), OutContract.PlayerHitRadius, OutError)
        || !RequiredNumber(Player, TEXT("start_x"), TEXT("player"), OutContract.PlayerStartX, OutError)
        || !RequiredNumber(Player, TEXT("start_z"), TEXT("player"), OutContract.PlayerStartZ, OutError)
        || !RequiredNumber(Player, TEXT("auto_fire_damage"), TEXT("player"), OutContract.AutoFireDamage, OutError)
        || !RequiredNumber(Player, TEXT("auto_fire_interval_seconds"), TEXT("player"), OutContract.AutoFireIntervalSeconds, OutError))
    {
        return false;
    }

    static const TSet<FString> BossKeys = {
        TEXT("boss_id"), TEXT("display_name"), TEXT("max_health"), TEXT("position_x"), TEXT("position_z")
    };
    if (!ValidateKeys(Boss, BossKeys, TEXT("boss"), OutError)
        || !RequiredString(Boss, TEXT("boss_id"), TEXT("boss"), OutContract.BossId, OutError)
        || !RequiredString(Boss, TEXT("display_name"), TEXT("boss"), OutContract.BossName, OutError)
        || !RequiredNumber(Boss, TEXT("max_health"), TEXT("boss"), OutContract.BossMaxHealth, OutError)
        || !RequiredNumber(Boss, TEXT("position_x"), TEXT("boss"), OutContract.BossPositionX, OutError)
        || !RequiredNumber(Boss, TEXT("position_z"), TEXT("boss"), OutContract.BossPositionZ, OutError))
    {
        return false;
    }

    const TArray<TSharedPtr<FJsonValue>>* PhaseValues = nullptr;
    if (!Root->TryGetArrayField(TEXT("phases"), PhaseValues) || PhaseValues == nullptr)
    {
        OutError = TEXT("root.phases expected array.");
        return false;
    }
    if (PhaseValues->Num() < 2 || PhaseValues->Num() > 3)
    {
        OutError = TEXT("root.phases requires two or three entries.");
        return false;
    }

    double PreviousTrigger = 2.0;
    for (int32 Index = 0; Index < PhaseValues->Num(); ++Index)
    {
        const TSharedPtr<FJsonObject> PhaseObject = (*PhaseValues)[Index]->AsObject();
        const FString Path = FString::Printf(TEXT("phases[%d]"), Index);
        if (!PhaseObject.IsValid())
        {
            OutError = FString::Printf(TEXT("%s expected object."), *Path);
            return false;
        }
        static const TSet<FString> PhaseKeys = {
            TEXT("phase_id"), TEXT("display_name"), TEXT("trigger"), TEXT("pattern")
        };
        if (!ValidateKeys(PhaseObject, PhaseKeys, Path, OutError))
        {
            return false;
        }

        FBulletHellPhase Phase;
        TSharedPtr<FJsonObject> Trigger;
        TSharedPtr<FJsonObject> Pattern;
        if (!RequiredString(PhaseObject, TEXT("phase_id"), Path, Phase.PhaseId, OutError)
            || !RequiredString(PhaseObject, TEXT("display_name"), Path, Phase.DisplayName, OutError)
            || !RequiredObject(PhaseObject, TEXT("trigger"), Path, Trigger, OutError)
            || !RequiredObject(PhaseObject, TEXT("pattern"), Path, Pattern, OutError))
        {
            return false;
        }
        static const TSet<FString> TriggerKeys = {TEXT("type"), TEXT("value")};
        if (!ValidateKeys(Trigger, TriggerKeys, Path + TEXT(".trigger"), OutError)
            || !RequiredString(Trigger, TEXT("type"), Path + TEXT(".trigger"), Phase.TriggerType, OutError)
            || !RequiredNumber(Trigger, TEXT("value"), Path + TEXT(".trigger"), Phase.TriggerValue, OutError)
            || !ParsePattern(Pattern, Path + TEXT(".pattern"), Phase.Pattern, OutError))
        {
            return false;
        }
        if (Phase.TriggerType != TEXT("boss_hp_below")
            || Phase.TriggerValue <= 0.0
            || Phase.TriggerValue > 1.0
            || Phase.TriggerValue > PreviousTrigger)
        {
            OutError = FString::Printf(TEXT("%s.trigger is invalid or out of order."), *Path);
            return false;
        }
        PreviousTrigger = Phase.TriggerValue;
        OutContract.Phases.Add(MoveTemp(Phase));
    }

    static const TSet<FString> ConstraintKeys = {
        TEXT("max_alive_bullets"), TEXT("min_fps"), TEXT("max_player_hits")
    };
    if (!ValidateKeys(Constraints, ConstraintKeys, TEXT("constraints"), OutError)
        || !RequiredNumber(Constraints, TEXT("max_alive_bullets"), TEXT("constraints"), OutContract.MaxAliveBullets, OutError)
        || !RequiredNumber(Constraints, TEXT("min_fps"), TEXT("constraints"), OutContract.MinimumFps, OutError)
        || !RequiredNumber(Constraints, TEXT("max_player_hits"), TEXT("constraints"), OutContract.MaxPlayerHits, OutError))
    {
        return false;
    }

    static const TSet<FString> TargetKeys = {
        TEXT("max_alive_bullets"), TEXT("max_player_hits"), TEXT("min_survival_seconds"),
        TEXT("min_fps"), TEXT("require_all_phases")
    };
    int32 TargetMaxAlive = 0;
    int32 TargetMaxHits = 0;
    double TargetMinFps = 0.0;
    if (!ValidateKeys(RuntimeTargets, TargetKeys, TEXT("runtime_targets"), OutError)
        || !RequiredNumber(RuntimeTargets, TEXT("max_alive_bullets"), TEXT("runtime_targets"), TargetMaxAlive, OutError)
        || !RequiredNumber(RuntimeTargets, TEXT("max_player_hits"), TEXT("runtime_targets"), TargetMaxHits, OutError)
        || !RequiredNumber(RuntimeTargets, TEXT("min_survival_seconds"), TEXT("runtime_targets"), OutContract.MinimumSurvivalSeconds, OutError)
        || !RequiredNumber(RuntimeTargets, TEXT("min_fps"), TEXT("runtime_targets"), TargetMinFps, OutError)
        || !RequiredBool(RuntimeTargets, TEXT("require_all_phases"), TEXT("runtime_targets"), OutContract.RequireAllPhases, OutError))
    {
        return false;
    }
    if (TargetMaxAlive > OutContract.MaxAliveBullets
        || TargetMaxHits > OutContract.MaxPlayerHits
        || TargetMinFps < OutContract.MinimumFps)
    {
        OutError = TEXT("runtime_targets cannot weaken constraints.");
        return false;
    }
    if (OutContract.DurationSeconds < 30.0 || OutContract.DurationSeconds > 60.0)
    {
        OutError = TEXT("scenario.duration_seconds must be within 30..60.");
        return false;
    }
    return true;
}
