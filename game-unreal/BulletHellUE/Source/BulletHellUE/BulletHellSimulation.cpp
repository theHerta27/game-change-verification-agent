#include "BulletHellSimulation.h"

void FBulletHellSimulation::Initialize(const FBulletHellContract& InContract, int32 InSeed)
{
    Contract = InContract;
    Random.Initialize(InSeed);
    Projectiles.Reset();
    FinishedPhases.Reset();
    CurrentPhaseIndex = 0;
    WaveIndex = 0;
    BossHealth = Contract.BossMaxHealth;
    PlayerHealth = Contract.PlayerMaxHealth;
    TotalBulletsSpawned = 0;
    PeakAliveBullets = 0;
    PlayerHits = 0;
    ElapsedSeconds = 0.0;
    NextPlayerShot = 0.0;
    UntilNextWave = 0.0;
    InvulnerableUntil = 0.0;
    bFinished = false;
    bCompletedScenario = false;
    BeginPhase(0);
}

void FBulletHellSimulation::Step(double DeltaSeconds, const FVector2D& PlayerPosition)
{
    if (bFinished)
    {
        return;
    }
    const float FixedStep = static_cast<float>(DeltaSeconds);
    ElapsedSeconds = static_cast<double>(
        static_cast<float>(ElapsedSeconds) + FixedStep);
    UpdateBossDamage();
    SelectPhase();

    UntilNextWave = static_cast<double>(
        static_cast<float>(UntilNextWave) - FixedStep);
    if (UntilNextWave <= 0.0)
    {
        EmitWave(PlayerPosition);
        UntilNextWave = static_cast<double>(
            static_cast<float>(GetCurrentPhase().Pattern.WaveIntervalMs) / 1000.0f);
    }
    StepProjectiles(DeltaSeconds, PlayerPosition);

    const int32 Active = Projectiles.Num();
    PeakAliveBullets = FMath::Max(PeakAliveBullets, Active);
    CurrentPhaseTelemetry.PeakAliveBullets = FMath::Max(CurrentPhaseTelemetry.PeakAliveBullets, Active);

    if (PlayerHealth <= 0)
    {
        bFinished = true;
        bCompletedScenario = false;
    }
    else if (ElapsedSeconds >= Contract.DurationSeconds || BossHealth <= 0)
    {
        ElapsedSeconds = FMath::Min(ElapsedSeconds, Contract.DurationSeconds);
        bFinished = true;
        bCompletedScenario = true;
    }
}

FVector2D FBulletHellSimulation::AutomaticPlayerPosition() const
{
    const float Elapsed = static_cast<float>(ElapsedSeconds);
    const float X = FMath::Sin(Elapsed * 0.72f)
        * static_cast<float>(Contract.ArenaWidth) * 0.34f;
    const float ZOffset = FMath::Sin(Elapsed * 0.39f)
        * static_cast<float>(Contract.ArenaHeight) * 0.1f;
    return FVector2D(X, static_cast<float>(Contract.PlayerStartZ) + ZOffset);
}

double FBulletHellSimulation::GetBossHealthRatio() const
{
    return Contract.BossMaxHealth > 0
        ? static_cast<double>(BossHealth) / static_cast<double>(Contract.BossMaxHealth)
        : 0.0;
}

TArray<FBulletHellPhaseTelemetry> FBulletHellSimulation::FinalizePhases()
{
    if (!CurrentPhaseTelemetry.PhaseId.IsEmpty())
    {
        CurrentPhaseTelemetry.DurationSeconds =
            FMath::Max(0.0, ElapsedSeconds - CurrentPhaseTelemetry.StartedAtSeconds);
        FinishedPhases.Add(CurrentPhaseTelemetry);
        CurrentPhaseTelemetry = FBulletHellPhaseTelemetry();
    }
    return FinishedPhases;
}

void FBulletHellSimulation::UpdateBossDamage()
{
    const float Elapsed = static_cast<float>(ElapsedSeconds);
    if (Elapsed < static_cast<float>(NextPlayerShot))
    {
        return;
    }
    NextPlayerShot = static_cast<double>(
        Elapsed + static_cast<float>(Contract.AutoFireIntervalSeconds));
    BossHealth = FMath::Max(0, BossHealth - Contract.AutoFireDamage);
}

void FBulletHellSimulation::SelectPhase()
{
    int32 NewIndex = 0;
    const double HealthRatio = GetBossHealthRatio();
    for (int32 Index = 0; Index < Contract.Phases.Num(); ++Index)
    {
        if (HealthRatio <= Contract.Phases[Index].TriggerValue)
        {
            NewIndex = Index;
        }
    }
    if (NewIndex != CurrentPhaseIndex)
    {
        BeginPhase(NewIndex);
    }
}

void FBulletHellSimulation::EmitWave(const FVector2D& PlayerPosition)
{
    const FBulletHellPattern& Pattern = GetCurrentPhase().Pattern;
    const FVector2D Origin(Contract.BossPositionX, Contract.BossPositionZ);
    const double TargetAngle = FMath::RadiansToDegrees(
        FMath::Atan2(PlayerPosition.Y - Origin.Y, PlayerPosition.X - Origin.X));
    const int32 Directions = Pattern.Bidirectional ? 2 : 1;
    int32 Spawned = 0;

    for (int32 DirectionIndex = 0; DirectionIndex < Directions; ++DirectionIndex)
    {
        const double DirectionSign = DirectionIndex == 0 ? 1.0 : -1.0;
        for (int32 Layer = 0; Layer < Pattern.LayerCount; ++Layer)
        {
            const double LayerOffset =
                Layer * (180.0 / FMath::Max(1, Pattern.BulletsPerWave * Pattern.LayerCount));
            const double Rotation = WaveIndex * Pattern.RotationPerWaveDeg * DirectionSign;
            for (int32 Index = 0; Index < Pattern.BulletsPerWave; ++Index)
            {
                double Angle = 0.0;
                if (Pattern.Type == TEXT("aimed_fan"))
                {
                    const double Step = Pattern.BulletsPerWave == 1
                        ? 0.0
                        : Pattern.SpreadAngleDeg / (Pattern.BulletsPerWave - 1);
                    Angle = TargetAngle - Pattern.SpreadAngleDeg * 0.5 + Index * Step + LayerOffset;
                }
                else
                {
                    const double RadialStep = Pattern.SpreadAngleDeg / Pattern.BulletsPerWave;
                    const double Wave = Pattern.Type == TEXT("petal")
                        ? FMath::Sin(Index * UE_TWO_PI / Pattern.BulletsPerWave) * 12.0
                        : 0.0;
                    Angle = Rotation + LayerOffset + Index * RadialStep + Wave;
                }

                const double Radians = FMath::DegreesToRadians(Angle);
                const double SpeedMultiplier = Pattern.Type == TEXT("petal")
                    ? 1.0 + Layer * 0.16
                    : 1.0;
                FBulletHellProjectile Projectile;
                Projectile.Position = Origin;
                Projectile.Velocity = FVector2D(FMath::Cos(Radians), FMath::Sin(Radians))
                    * Pattern.BulletSpeed * SpeedMultiplier;
                Projectile.RemainingLifetime = Pattern.BulletLifetimeSeconds;
                Projectiles.Add(Projectile);
                ++Spawned;
            }
        }
    }
    ++WaveIndex;
    TotalBulletsSpawned += Spawned;
    CurrentPhaseTelemetry.BulletsSpawned += Spawned;
}

void FBulletHellSimulation::StepProjectiles(
    double DeltaSeconds,
    const FVector2D& PlayerPosition)
{
    int32 HitsThisStep = 0;
    for (int32 Index = Projectiles.Num() - 1; Index >= 0; --Index)
    {
        FBulletHellProjectile& Projectile = Projectiles[Index];
        const FVector2D NextPosition = Projectile.Position
            + Projectile.Velocity * static_cast<float>(DeltaSeconds);
        Projectile.Position.X = static_cast<float>(NextPosition.X);
        Projectile.Position.Y = static_cast<float>(NextPosition.Y);
        Projectile.RemainingLifetime = static_cast<double>(
            static_cast<float>(Projectile.RemainingLifetime)
            - static_cast<float>(DeltaSeconds));

        const bool bHit = FVector2D::DistSquared(Projectile.Position, PlayerPosition)
            <= FMath::Square(Contract.PlayerHitRadius);
        const bool bExpired = Projectile.RemainingLifetime <= 0.0
            || FMath::Abs(Projectile.Position.X) > Contract.ArenaWidth * 0.65
            || FMath::Abs(Projectile.Position.Y) > Contract.ArenaHeight * 0.65;
        if (bHit)
        {
            ++HitsThisStep;
        }
        if (bHit || bExpired)
        {
            Projectiles.RemoveAt(Index, 1, EAllowShrinking::No);
        }
    }

    if (HitsThisStep > 0 && ElapsedSeconds >= InvulnerableUntil)
    {
        InvulnerableUntil = ElapsedSeconds + 0.35;
        --PlayerHealth;
        ++PlayerHits;
        ++CurrentPhaseTelemetry.PlayerHits;
    }
}

void FBulletHellSimulation::BeginPhase(int32 NewPhaseIndex)
{
    if (!CurrentPhaseTelemetry.PhaseId.IsEmpty())
    {
        CurrentPhaseTelemetry.DurationSeconds =
            FMath::Max(0.0, ElapsedSeconds - CurrentPhaseTelemetry.StartedAtSeconds);
        FinishedPhases.Add(CurrentPhaseTelemetry);
    }
    CurrentPhaseIndex = NewPhaseIndex;
    WaveIndex = 0;
    UntilNextWave = 0.0;
    CurrentPhaseTelemetry = FBulletHellPhaseTelemetry();
    CurrentPhaseTelemetry.PhaseId = Contract.Phases[NewPhaseIndex].PhaseId;
    CurrentPhaseTelemetry.PatternType = Contract.Phases[NewPhaseIndex].Pattern.Type;
    CurrentPhaseTelemetry.StartedAtSeconds = ElapsedSeconds;
}
