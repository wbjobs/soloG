using System.Collections;
using System.Collections.Generic;

namespace ConfigCenter.Infrastructure.Caching;

public interface IConfigCache
{
    bool TryGet(string key, EnvironmentType environment, out string? value, out int version);
    void Set(string key, EnvironmentType environment, string value, int version);
    void Invalidate(string key, EnvironmentType environment);
    void InvalidateAll();
    void InvalidateEnvironment(EnvironmentType environment);
}

public class LruConfigCache : IConfigCache
{
    private readonly int _capacity;
    private readonly Dictionary<CacheKey, CacheItem> _cache;
    private readonly LinkedList<CacheKey> _lruList;
    private readonly object _lock = new();

    public LruConfigCache(int capacity = 1000)
    {
        _capacity = capacity;
        _cache = new Dictionary<CacheKey, CacheItem>(capacity);
        _lruList = new LinkedList<CacheKey>();
    }

    public bool TryGet(string key, EnvironmentType environment, out string? value, out int version)
    {
        lock (_lock)
        {
            var cacheKey = new CacheKey(key, environment);
            if (_cache.TryGetValue(cacheKey, out var item))
            {
                _lruList.Remove(cacheKey);
                _lruList.AddFirst(cacheKey);
                value = item.Value;
                version = item.Version;
                return true;
            }
            value = null;
            version = 0;
            return false;
        }
    }

    public void Set(string key, EnvironmentType environment, string value, int version)
    {
        lock (_lock)
        {
            var cacheKey = new CacheKey(key, environment);
            if (_cache.TryGetValue(cacheKey, out var existing))
            {
                if (existing.Version >= version)
                    return;
                _lruList.Remove(cacheKey);
                _cache[cacheKey] = new CacheItem(value, version);
                _lruList.AddFirst(cacheKey);
            }
            else
            {
                if (_cache.Count >= _capacity)
                {
                    var last = _lruList.Last!;
                    _cache.Remove(last.Value);
                    _lruList.RemoveLast();
                }
                _cache[cacheKey] = new CacheItem(value, version);
                _lruList.AddFirst(cacheKey);
            }
        }
    }

    public void Invalidate(string key, EnvironmentType environment)
    {
        lock (_lock)
        {
            var cacheKey = new CacheKey(key, environment);
            if (_cache.Remove(cacheKey))
            {
                _lruList.Remove(cacheKey);
            }
        }
    }

    public void InvalidateAll()
    {
        lock (_lock)
        {
            _cache.Clear();
            _lruList.Clear();
        }
    }

    public void InvalidateEnvironment(EnvironmentType environment)
    {
        lock (_lock)
        {
            var toRemove = _cache.Keys.Where(k => k.Environment == environment).ToList();
            foreach (var key in toRemove)
            {
                _cache.Remove(key);
                _lruList.Remove(key);
            }
        }
    }

    private readonly struct CacheKey : IEquatable<CacheKey>
    {
        public string Key { get; }
        public EnvironmentType Environment { get; }

        public CacheKey(string key, EnvironmentType environment)
        {
            Key = key;
            Environment = environment;
        }

        public bool Equals(CacheKey other)
        {
            return Key == other.Key && Environment == other.Environment;
        }

        public override bool Equals(object? obj)
        {
            return obj is CacheKey other && Equals(other);
        }

        public override int GetHashCode()
        {
            return HashCode.Combine(Key, Environment);
        }

        public static bool operator ==(CacheKey left, CacheKey right)
        {
            return left.Equals(right);
        }

        public static bool operator !=(CacheKey left, CacheKey right)
        {
            return !left.Equals(right);
        }
    }

    private class CacheItem
    {
        public string Value { get; }
        public int Version { get; }

        public CacheItem(string value, int version)
        {
            Value = value;
            Version = version;
        }
    }
}
