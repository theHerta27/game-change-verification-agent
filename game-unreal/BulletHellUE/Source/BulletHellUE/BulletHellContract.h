#pragma once

#include "CoreMinimal.h"

struct FBulletHellPattern
{
    FString Type;
    int32 BulletsPerWave = 0;
    int32 WaveIntervalMs = 0;
    double BulletSpeed = 0.0;
    double BulletLifetimeSeconds = 0.0;
    double RotationPerWaveDeg = 0.0;
    double SpreadAngleDeg = 0.0;
    int32 LayerCount = 0;
    bool Bidirectional = false;
};

struct FBulletHellPhase
{
    FString PhaseId;
    FString DisplayName;
    FString TriggerType;
    double TriggerValue = 0.0;
    FBulletHellPattern Pattern;
};

struct FBulletHellContract
{
    FString ContractVersion;
    FString ScenarioId;
    FString ScenarioName;
    double DurationSeconds = 0.0;
    double ArenaWidth = 0.0;
    double ArenaHeight = 0.0;

    int32 PlayerMaxHealth = 0;
    double PlayerMoveSpeed = 0.0;
    double FocusSpeedMultiplier = 0.0;
    double PlayerHitRadius = 0.0;
    double PlayerStartX = 0.0;
    double PlayerStartZ = 0.0;
    int32 AutoFireDamage = 0;
    double AutoFireIntervalSeconds = 0.0;

    FString BossId;
    FString BossName;
    int32 BossMaxHealth = 0;
    double BossPositionX = 0.0;
    double BossPositionZ = 0.0;

    TArray<FBulletHellPhase> Phases;
    int32 MaxAliveBullets = 0;
    double MinimumFps = 0.0;
    int32 MaxPlayerHits = 0;
    double MinimumSurvivalSeconds = 0.0;
    bool RequireAllPhases = false;

    static bool LoadStrict(const FString& FilePath, FBulletHellContract& OutContract, FString& OutError);
};
