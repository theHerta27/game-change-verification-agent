namespace GameConfig.Runtime
{
    public sealed class BossPhaseController
    {
        private readonly BulletHellPhase[] phases;
        private readonly int maxHealth;

        public int Health { get; private set; }
        public int CurrentIndex { get; private set; }
        public BulletHellPhase CurrentPhase => phases[CurrentIndex];
        public float HealthRatio => (float)Health / maxHealth;

        public BossPhaseController(BulletHellPhase[] phases, int maxHealth)
        {
            this.phases = phases;
            this.maxHealth = maxHealth;
            Health = maxHealth;
            CurrentIndex = 0;
        }

        public bool ApplyDamage(int damage)
        {
            Health = System.Math.Max(0, Health - damage);
            int nextIndex = 0;
            for (int index = 0; index < phases.Length; index++)
            {
                if (HealthRatio <= phases[index].trigger.value) nextIndex = index;
            }
            if (nextIndex == CurrentIndex) return false;
            CurrentIndex = nextIndex;
            return true;
        }
    }
}
