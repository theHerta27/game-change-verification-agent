using System.Collections.Generic;
using UnityEngine;

namespace GameConfig.Runtime
{
    public sealed class ProjectilePool
    {
        private readonly List<ProjectileController> projectiles = new();
        private readonly Transform parent;
        private readonly Material material;

        public ProjectilePool(Transform parent, Material material, int initialSize)
        {
            this.parent = parent;
            this.material = material;
            for (int index = 0; index < initialSize; index++) CreateProjectile();
        }

        public int ActiveCount
        {
            get
            {
                int count = 0;
                foreach (ProjectileController projectile in projectiles)
                    if (projectile.IsActive) count++;
                return count;
            }
        }

        public void Spawn(Vector3 position, Vector3 direction, float speed, float lifetime)
        {
            ProjectileController projectile = projectiles.Find(item => !item.IsActive);
            if (projectile == null) projectile = CreateProjectile();
            projectile.Activate(position, direction, speed, lifetime, material);
        }

        public int StepAll(float deltaTime, Vector3 playerPosition, float hitRadius, float arenaWidth, float arenaHeight)
        {
            int hits = 0;
            foreach (ProjectileController projectile in projectiles)
            {
                if (!projectile.IsActive) continue;
                ProjectileStepResult result = projectile.Step(deltaTime, playerPosition, hitRadius, arenaWidth, arenaHeight);
                if (result == ProjectileStepResult.Active) continue;
                if (result == ProjectileStepResult.HitPlayer) hits++;
                projectile.gameObject.SetActive(false);
            }
            return hits;
        }

        public void Clear()
        {
            foreach (ProjectileController projectile in projectiles)
                projectile.gameObject.SetActive(false);
        }

        private ProjectileController CreateProjectile()
        {
            GameObject view = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            view.name = "Pooled Bullet";
            view.transform.SetParent(parent, false);
            view.transform.localScale = Vector3.one * 0.22f;
            Object.Destroy(view.GetComponent<Collider>());
            view.GetComponent<Renderer>().sharedMaterial = material;
            ProjectileController projectile = view.AddComponent<ProjectileController>();
            view.SetActive(false);
            projectiles.Add(projectile);
            return projectile;
        }
    }
}
