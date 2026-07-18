using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using GameConfig.Runtime;
using UnityEditor;
using UnityEngine;

namespace GameConfig.Editor
{
    public static class LocalReimuImporter
    {
        private const string ModelPath = "Assets/Resources/LocalThirdParty/Reimu/Model/Reimu_Spring.fbx";
        private const string PrefabPath = "Assets/Resources/LocalThirdParty/Reimu/Reimu.prefab";
        private const string MaterialDirectory = "Assets/Resources/LocalThirdParty/Reimu/Materials";
        private const string TextureDirectory = "Assets/Resources/LocalThirdParty/Reimu/Model";
        private const float TargetHeight = 2.0f;

        [Serializable]
        private sealed class ImportReport
        {
            public string status;
            public string generated_at_utc;
            public string model_path;
            public string prefab_path;
            public int renderer_count;
            public int skinned_renderer_count;
            public int material_count;
            public int bone_count;
            public float source_height;
            public float normalized_height;
            public float applied_scale;
            public int unsupported_shader_count;
            public int textures_bound_count;
            public int missing_texture_count;
            public bool resolver_uses_local_asset;
        }

        [MenuItem("GameConfig/Import Local Reimu Presentation")]
        public static void ImportAndValidate()
        {
            if (!File.Exists(ModelPath)) throw new FileNotFoundException("Local Reimu FBX was not found.", ModelPath);
            AssetDatabase.ImportAsset(ModelPath, ImportAssetOptions.ForceSynchronousImport | ImportAssetOptions.ForceUpdate);

            ModelImporter importer = AssetImporter.GetAtPath(ModelPath) as ModelImporter;
            if (importer == null) throw new InvalidDataException("Unity did not create a ModelImporter for the Reimu FBX.");
            importer.importAnimation = false;
            importer.importBlendShapes = true;
            importer.importCameras = false;
            importer.importLights = false;
            importer.animationType = ModelImporterAnimationType.Generic;
            importer.SaveAndReimport();
            Material[] sourceMaterials = AssetDatabase.LoadAllAssetsAtPath(ModelPath).OfType<Material>().ToArray();
            MaterialBindingResult materialBinding = BindLocalMaterials(importer, sourceMaterials);

            GameObject modelAsset = AssetDatabase.LoadAssetAtPath<GameObject>(ModelPath);
            if (modelAsset == null) throw new InvalidDataException("Unity could not load the imported Reimu model asset.");

            GameObject wrapper = new("Reimu");
            GameObject model = PrefabUtility.InstantiatePrefab(modelAsset) as GameObject;
            if (model == null) throw new InvalidDataException("Unity could not instantiate the imported Reimu model.");
            model.name = "Model";
            model.transform.SetParent(wrapper.transform, false);

            Bounds sourceBounds = CalculateBounds(model);
            if (sourceBounds.size.y <= 0.001f) throw new InvalidDataException("Imported Reimu model has invalid bounds.");
            float scale = TargetHeight / sourceBounds.size.y;
            model.transform.localScale *= scale;
            Bounds normalizedBounds = CalculateBounds(model);
            model.transform.position += Vector3.up * -normalizedBounds.min.y;
            normalizedBounds = CalculateBounds(model);

            LocalCharacterPresentation presentation = wrapper.AddComponent<LocalCharacterPresentation>();
            presentation.Configure(model.transform);
            Directory.CreateDirectory(Path.GetDirectoryName(PrefabPath));
            GameObject prefab = PrefabUtility.SaveAsPrefabAsset(wrapper, PrefabPath);
            UnityEngine.Object.DestroyImmediate(wrapper);
            if (prefab == null) throw new InvalidDataException("Unity failed to save the local Reimu prefab.");

            Renderer[] renderers = prefab.GetComponentsInChildren<Renderer>(true);
            SkinnedMeshRenderer[] skinned = prefab.GetComponentsInChildren<SkinnedMeshRenderer>(true);
            Material[] materials = renderers.SelectMany(renderer => renderer.sharedMaterials).Where(material => material != null).Distinct().ToArray();
            int unsupportedShaders = materials.Count(material => material.shader == null || !material.shader.isSupported);
            int bones = skinned.Sum(renderer => renderer.bones?.Length ?? 0);

            CharacterViewResolution resolution = CharacterViewResolver.ResolveFromCandidates(prefab, null, Vector3.zero, null);
            bool usesLocal = resolution.UsesLocalAsset && resolution.View != null;
            if (resolution.View != null) UnityEngine.Object.DestroyImmediate(resolution.View);
            if (!usesLocal) throw new InvalidDataException("CharacterViewResolver did not select the local Reimu prefab.");

            ImportReport report = new()
            {
                status = unsupportedShaders == 0 ? "completed" : "completed_with_shader_warnings",
                generated_at_utc = DateTime.UtcNow.ToString("O"),
                model_path = ModelPath,
                prefab_path = PrefabPath,
                renderer_count = renderers.Length,
                skinned_renderer_count = skinned.Length,
                material_count = materials.Length,
                bone_count = bones,
                source_height = sourceBounds.size.y,
                normalized_height = normalizedBounds.size.y,
                applied_scale = scale,
                unsupported_shader_count = unsupportedShaders,
                textures_bound_count = materialBinding.TexturesBound,
                missing_texture_count = materialBinding.MissingTextures,
                resolver_uses_local_asset = usesLocal,
            };
            string reportPath = ResolveReportPath();
            Directory.CreateDirectory(Path.GetDirectoryName(reportPath));
            File.WriteAllText(reportPath, JsonUtility.ToJson(report, true));
            AssetDatabase.SaveAssets();
            Debug.Log($"Local Reimu import passed. Prefab: {PrefabPath}. Report: {reportPath}");
        }

        private readonly struct MaterialBindingResult
        {
            public int TexturesBound { get; }
            public int MissingTextures { get; }

            public MaterialBindingResult(int texturesBound, int missingTextures)
            {
                TexturesBound = texturesBound;
                MissingTextures = missingTextures;
            }
        }

        private static MaterialBindingResult BindLocalMaterials(ModelImporter importer, Material[] sourceMaterials)
        {
            if (AssetDatabase.IsValidFolder(MaterialDirectory)) AssetDatabase.DeleteAsset(MaterialDirectory);
            Directory.CreateDirectory(MaterialDirectory);
            AssetDatabase.Refresh();
            Shader shader = Shader.Find("Standard");
            if (shader == null) throw new InvalidDataException("Unity Standard shader is unavailable.");

            int texturesBound = 0;
            int missingTextures = 0;
            for (int index = 0; index < sourceMaterials.Length; index++)
            {
                Material source = sourceMaterials[index];
                string textureName = TextureNameForMaterial(source.name);
                Texture2D texture = AssetDatabase.LoadAssetAtPath<Texture2D>($"{TextureDirectory}/{textureName}");
                if (texture == null) missingTextures++; else texturesBound++;

                Material material = new(shader)
                {
                    name = $"Reimu_{index:00}",
                    color = Color.white,
                    mainTexture = texture,
                    enableInstancing = true,
                };
                if (source.name.Contains("ハイライト") || source.name.Contains("髪")) ConfigureCutout(material);
                string materialPath = $"{MaterialDirectory}/Reimu_{index:00}.mat";
                AssetDatabase.CreateAsset(material, materialPath);
                importer.AddRemap(new AssetImporter.SourceAssetIdentifier(typeof(Material), source.name), material);
            }
            importer.SaveAndReimport();
            return new MaterialBindingResult(texturesBound, missingTextures);
        }

        private static string TextureNameForMaterial(string materialName)
        {
            if (materialName.Contains("ハイライト")) return "rm_hl.tga";
            if (materialName.Contains("髪")) return "rm_hair.tga";
            if (materialName.Contains("顔") || materialName.Contains("白目") || materialName.Contains("瞳")) return "rm_face.bmp";
            if (materialName.Contains("春服") || materialName.Contains("袖") || materialName.Contains("靴")) return "rm_spri.bmp";
            if (materialName.Contains("武器")) return "rm_wp.bmp";
            return "rm_body.bmp";
        }

        private static void ConfigureCutout(Material material)
        {
            material.SetFloat("_Mode", 1f);
            material.SetFloat("_Cutoff", 0.35f);
            material.SetOverrideTag("RenderType", "TransparentCutout");
            material.EnableKeyword("_ALPHATEST_ON");
            material.DisableKeyword("_ALPHABLEND_ON");
            material.DisableKeyword("_ALPHAPREMULTIPLY_ON");
            material.renderQueue = 2450;
        }

        private static Bounds CalculateBounds(GameObject root)
        {
            Renderer[] renderers = root.GetComponentsInChildren<Renderer>(true);
            if (renderers.Length == 0) return new Bounds(root.transform.position, Vector3.zero);
            Bounds bounds = renderers[0].bounds;
            foreach (Renderer renderer in renderers.Skip(1)) bounds.Encapsulate(renderer.bounds);
            return bounds;
        }

        private static string ResolveReportPath()
        {
            string[] args = Environment.GetCommandLineArgs();
            int index = Array.IndexOf(args, "--reimu-report");
            return index >= 0 && index + 1 < args.Length
                ? Path.GetFullPath(args[index + 1])
                : Path.GetFullPath("../runtime-artifacts/reimu-import/unity_import_report.json");
        }
    }
}
