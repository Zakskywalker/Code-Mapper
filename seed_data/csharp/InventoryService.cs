using System;
using System.Collections.Generic;

namespace Seed.Inventory {
    public class InventoryService {
        private readonly Dictionary<string, Product> _catalog = new();
        public event Action<string>? LowStock;

        public void AddProduct(string sku, string name, int quantity) {
            _catalog[sku] = new Product { Sku = sku, Name = name, Quantity = quantity };
        }

        public bool Reserve(string sku, int amount) {
            if (!_catalog.ContainsKey(sku)) return false;
            var p = _catalog[sku];
            if (p.Quantity < amount) return false;
            p.Quantity -= amount;
            if (p.Quantity < 5) LowStock?.Invoke(sku);
            return true;
        }

        public IReadOnlyCollection<Product> ListAll() => _catalog.Values;
    }

    public class Product {
        public string Sku { get; set; } = string.Empty;
        public string Name { get; set; } = string.Empty;
        public int Quantity { get; set; }
    }
}
