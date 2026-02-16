export class Store {
  private items: string[] = [];
  add(item: string) { this.items.push(item); }
  list(): string[] { return this.items; }
}
