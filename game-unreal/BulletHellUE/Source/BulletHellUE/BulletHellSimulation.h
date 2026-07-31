#pragma once

#include "CoreMinimal.h"
#include "BulletHellContract.h"

struct FBulletHellProjectile
{
    FVector2D Position = FVector2D::ZeroVector;
    FVector2D Velocity = FVector2D::ZeroVector;
    double RemainingLifetime = 0.0;
};

struct FBulletHellPhaseTelemetry
{
    FString PhaseId;
    FString PatternType;
    double StartedAtSeconds = 0.0;
    double DurationSeconds = 0.0;
    int32 BulletsSpawned = 0;
    int32 PlayerHits = 0;
    int32 PeakAliveBullets = 0;
};

class FBulletHellSimulation
{
public:
    void Initialize(const FBulletHellContract& InContract, int32 InSeed);
    void Step(double DeltaSeconds, const FVector2D& PlayerPosition);

    FVector2D AutomaticPlayerPosition() const;
    const TArray<FBulletHellProjectile>& GetProjectiles() const { return Projectiles; }
    const FBulletHellPhase& GetCurrentPhase() const { return Contract.Phases[CurrentPhaseIndex]; }
    const TArray<FBulletHellPhaseTelemetry>& GetFinishedPhases() const { return FinishedPhases; }
    const FBulletHellPhaseTelemetry& GetCurrentPhaseTelemetry() const { return CurrentPhaseTelemetry; }

    double GetElapsedSeconds() const { return ElapsedSeconds; }
    int32 GetBossHealth() const { return BossHealth; }
    double GetBossHealthRatio() const;
    int32 GetPlayerHealth() const { return PlayerHealth; }
    int32 GetTotalBulletsSpawned() const { return TotalBulletsSpawned; }
    int32 GetPeakAliveBullets() const { return PeakAliveBullets; }
    int32 GetPlayerHits() const { return PlayerHits; }
    bool IsFinished() const { return bFinished; }
    bool DidCompleteScenario() const { return bCompletedScenario; }

    TArray<FBulletHellPhaseTelemetry> FinalizePhases();

private:
    void UpdateBossDamage();
    void SelectPhase();
    void EmitWave(const FVector2D& PlayerPosition);
    void StepProjectiles(double DeltaSeconds, const FVector2D& PlayerPosition);
    void BeginPhase(int32 NewPhaseIndex);

    FBulletHellContract Contract;
    FRandomStream Random;
    TArray<FBulletHellProjectile> Projectiles;
    TArray<FBulletHellPhaseTelemetry> FinishedPhases;
    FBulletHellPhaseTelemetry CurrentPhaseTelemetry;
    int32 CurrentPhaseIndex = 0;
    int32 WaveIndex = 0;
    int32 BossHealth = 0;
    int32 PlayerHealth = 0;
    int32 TotalBulletsSpawned = 0;
    int32 PeakAliveBullets = 0;
    int32 PlayerHits = 0;
    double ElapsedSeconds = 0.0;
    double NextPlayerShot = 0.0;
    double UntilNextWave = 0.0;
    double InvulnerableUntil = 0.0;
    bool bFinished = false;
    bool bCompletedScenario = false;
};
