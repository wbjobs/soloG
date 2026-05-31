using System.Text.RegularExpressions;
using ConfigCenter.Core.DTOs;
using ConfigCenter.Core.Enums;
using ConfigCenter.Core.Interfaces;
using ConfigCenter.Infrastructure.Data;
using Microsoft.EntityFrameworkCore;

namespace ConfigCenter.Infrastructure.Services;

public class DependencyAnalyzer : IDependencyAnalyzer
{
    private readonly ConfigCenterDbContext _db;
    private readonly IEncryptionService _encryption;

    private static readonly Regex[] ReferencePatterns = new[]
    {
        new Regex(@"\$\{([^}]+)\}", RegexOptions.Compiled),
        new Regex(@"\{\{([^}]+)\}\}", RegexOptions.Compiled),
        new Regex(@"%%([^%]+)%%", RegexOptions.Compiled),
        new Regex(@"@\(([^)]+)\)", RegexOptions.Compiled)
    };

    public DependencyAnalyzer(ConfigCenterDbContext db, IEncryptionService encryption)
    {
        _db = db;
        _encryption = encryption;
    }

    public async Task<DependencyGraphDto> AnalyzeAsync(EnvironmentType environment, CancellationToken ct = default)
    {
        var configs = await _db.ConfigEntries
            .Where(c => c.Environment == environment && !c.IsDeleted)
            .ToListAsync(ct);

        var configDict = configs.ToDictionary(c => c.Key, c => c);
        var allKeys = configs.Select(c => c.Key).ToHashSet();

        var graph = new DependencyGraphDto
        {
            Nodes = allKeys.ToList()
        };

        var edges = new List<DependencyDto>();
        var dependencies = new Dictionary<string, List<string>>();
        var dependents = new Dictionary<string, List<string>>();

        foreach (var key in allKeys)
        {
            dependencies[key] = new List<string>();
            dependents[key] = new List<string>();
        }

        foreach (var config in configs)
        {
            var value = config.IsEncrypted ? _encryption.Decrypt(config.Value) : config.Value;
            var references = ExtractReferences(value, allKeys);

            foreach (var targetKey in references)
            {
                var edge = new DependencyDto
                {
                    SourceKey = config.Key,
                    TargetKey = targetKey,
                    Type = DependencyType.Direct
                };
                edges.Add(edge);

                if (!dependencies[config.Key].Contains(targetKey))
                    dependencies[config.Key].Add(targetKey);
                if (!dependents[targetKey].Contains(config.Key))
                    dependents[targetKey].Add(config.Key);
            }
        }

        graph.Edges = edges;
        graph.Dependencies = dependencies;
        graph.Dependents = dependents;
        graph.CircularDependencies = FindCircularDependencies(dependencies);

        return graph;
    }

    public async Task<List<DependencyDto>> GetDependenciesAsync(string key, EnvironmentType environment, CancellationToken ct = default)
    {
        var graph = await AnalyzeAsync(environment, ct);
        var result = new List<DependencyDto>();

        if (graph.Dependencies.TryGetValue(key, out var deps))
        {
            foreach (var dep in deps)
            {
                result.Add(new DependencyDto
                {
                    SourceKey = key,
                    TargetKey = dep,
                    Type = DependencyType.Direct
                });
            }
        }

        var visited = new HashSet<string>(deps);
        var queue = new Queue<string>(deps);
        while (queue.Count > 0)
        {
            var current = queue.Dequeue();
            if (graph.Dependencies.TryGetValue(current, out var transitiveDeps))
            {
                foreach (var td in transitiveDeps)
                {
                    if (!visited.Contains(td))
                    {
                        visited.Add(td);
                        queue.Enqueue(td);
                        result.Add(new DependencyDto
                        {
                            SourceKey = key,
                            TargetKey = td,
                            Type = DependencyType.Transitive
                        });
                    }
                }
            }
        }

        return result;
    }

    public async Task<List<DependencyDto>> GetDependentsAsync(string key, EnvironmentType environment, CancellationToken ct = default)
    {
        var graph = await AnalyzeAsync(environment, ct);
        var result = new List<DependencyDto>();

        if (graph.Dependents.TryGetValue(key, out var deps))
        {
            foreach (var dep in deps)
            {
                result.Add(new DependencyDto
                {
                    SourceKey = dep,
                    TargetKey = key,
                    Type = DependencyType.Direct
                });
            }
        }

        return result;
    }

    public async Task<List<string>> FindCircularDependenciesAsync(EnvironmentType environment, CancellationToken ct = default)
    {
        var graph = await AnalyzeAsync(environment, ct);
        return graph.CircularDependencies;
    }

    private static HashSet<string> ExtractReferences(string value, HashSet<string> allKeys)
    {
        var references = new HashSet<string>();

        if (string.IsNullOrWhiteSpace(value))
            return references;

        foreach (var pattern in ReferencePatterns)
        {
            var matches = pattern.Matches(value);
            foreach (Match match in matches)
            {
                var refKey = match.Groups[1].Value.Trim();
                if (allKeys.Contains(refKey))
                {
                    references.Add(refKey);
                }
            }
        }

        return references;
    }

    private static List<string> FindCircularDependencies(Dictionary<string, List<string>> graph)
    {
        var cycles = new List<string>();
        var visited = new HashSet<string>();
        var recStack = new HashSet<string>();
        var path = new List<string>();

        foreach (var node in graph.Keys)
        {
            if (HasCycle(node, graph, visited, recStack, path, cycles))
            {
            }
        }

        return cycles.Distinct().ToList();
    }

    private static bool HasCycle(string node, Dictionary<string, List<string>> graph,
        HashSet<string> visited, HashSet<string> recStack, List<string> path, List<string> cycles)
    {
        if (recStack.Contains(node))
        {
            var cycleStart = path.IndexOf(node);
            if (cycleStart >= 0)
            {
                var cycle = path.Skip(cycleStart).ToList();
                cycle.Add(node);
                cycles.Add(string.Join(" → ", cycle));
            }
            return true;
        }

        if (visited.Contains(node))
            return false;

        visited.Add(node);
        recStack.Add(node);
        path.Add(node);

        if (graph.TryGetValue(node, out var neighbors))
        {
            foreach (var neighbor in neighbors)
            {
                if (HasCycle(neighbor, graph, visited, recStack, path, cycles))
                {
                }
            }
        }

        path.RemoveAt(path.Count - 1);
        recStack.Remove(node);
        return false;
    }
}
