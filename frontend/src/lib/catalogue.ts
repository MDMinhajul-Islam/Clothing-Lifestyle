import type { Product } from '../types/catalog';

export type StyleKind = 'dress' | 'outerwear' | 'top' | 'bottom' | 'shoes' | 'bag' | 'accessory' | 'beauty' | 'home';

const includesAny = (value: string, words: string[]) => words.some((word) => value.includes(word));

export function styleKind(product: Product): StyleKind {
  const text = `${product.name} ${product.category}`.toLowerCase();
  if (includesAny(text, ['board', 'towel', 'candle', 'candlestick', 'frame', 'home'])) return 'home';
  if (includesAny(text, ['perfume', 'parfum', 'edp', 'lipstick', 'eyeliner', 'beauty', 'smoothie'])) return 'beauty';
  if (includesAny(text, ['bag', 'pouch', 'tote', 'clutch'])) return 'bag';
  if (includesAny(text, ['shoe', 'boot', 'sneaker', 'loafer', 'flat', 'heel'])) return 'shoes';
  if (includesAny(text, ['dress', 'gown'])) return 'dress';
  if (includesAny(text, ['blazer', 'jacket', 'coat', 'parka'])) return 'outerwear';
  if (includesAny(text, ['pant', 'trouser', 'jean', 'skirt', 'legging', 'short'])) return 'bottom';
  if (includesAny(text, ['shirt', 'blouse', 'top', 'sweater', 'knit', 'jumpsuit', 'sweatshirt'])) return 'top';
  if (includesAny(text, ['belt', 'scarf', 'jewelry', 'necklace', 'earring', 'bonnet'])) return 'accessory';
  return 'accessory';
}

export const isMainFashionProduct = (product: Product) => !['home', 'beauty'].includes(styleKind(product));

const compatibility: Record<StyleKind, StyleKind[]> = {
  dress: ['shoes', 'bag', 'outerwear', 'accessory'],
  outerwear: ['top', 'bottom', 'shoes', 'bag'],
  top: ['bottom', 'outerwear', 'shoes', 'accessory'],
  bottom: ['top', 'outerwear', 'shoes', 'accessory'],
  shoes: ['dress', 'bottom', 'bag', 'outerwear'],
  bag: ['dress', 'shoes', 'outerwear'],
  accessory: ['dress', 'outerwear', 'top', 'bottom'],
  beauty: [],
  home: [],
};

export function compatibleProducts(product: Product, catalogue: Product[], limit = 4): Product[] {
  const allowed = compatibility[styleKind(product)];
  if (!allowed.length) return [];
  const sameDepartment = (candidate: Product) => candidate.department === product.department || candidate.department === 'UNISEX';
  return catalogue
    .filter((candidate) => candidate.id !== product.id && isMainFashionProduct(candidate) && allowed.includes(styleKind(candidate)) && sameDepartment(candidate))
    .sort((a, b) => Number(product.matchingProductIds?.includes(b.id)) - Number(product.matchingProductIds?.includes(a.id)))
    .slice(0, limit);
}

const colorFamilies: Record<string, string[]> = {
  black: ['black', 'charcoal', 'anthracite'], white: ['white', 'ecru', 'ivory', 'cream'],
  blue: ['blue', 'navy', 'indigo'], brown: ['brown', 'chocolate', 'camel', 'tan'],
  red: ['red', 'burgundy', 'wine'], green: ['green', 'olive', 'khaki'],
  pink: ['pink', 'rose'], yellow: ['yellow', 'mustard'], gray: ['gray', 'grey', 'charcoal'],
};

export function matchesColor(product: Product, selected: string): boolean {
  const target = selected.toLowerCase();
  const aliases = colorFamilies[target] ?? [target];
  return product.colors.some((color) => aliases.some((alias) => color.name.toLowerCase().includes(alias)));
}

export function matchesProductSearch(product: Product, query: string): boolean {
  const haystack = `${product.name} ${product.description} ${product.category} ${product.department}`.toLowerCase();
  const terms = query.toLowerCase().split(/\s+/).filter(Boolean).map((term) => term.endsWith('ies') ? `${term.slice(0, -3)}y` : term.endsWith('es') ? term.slice(0, -2) : term.endsWith('s') ? term.slice(0, -1) : term);
  return terms.every((term) => haystack.includes(term));
}
