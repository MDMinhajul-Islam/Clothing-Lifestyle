import type { Product, ProductFilter } from '../types/catalog';

const API_URL = (import.meta.env.VITE_BACKEND_API_URL || 'http://localhost:8000').replace(/\/$/, '');

interface ApiMatchedVariant { variant_id: string; sku?: string | null; color?: string | null; size?: string | null; availability_state: string; in_stock: boolean; image_url?: string | null; gallery_urls?: string[] | null; price?: number | null }
interface ApiProduct { product_id: string; name: string; department: string; category?: string | null; description?: string | null; price: number; original_price?: number | null; currency: string; colors: string[]; sizes: string[]; image_urls: string[]; available: boolean; is_on_sale: boolean; matched_variant?: ApiMatchedVariant | null; hero_video_url?: string | null; hero_media_url?: string | null; model_walk_url?: string | null; lookbook_media?: string[] | null }
interface ApiList { items: ApiProduct[]; total: number; limit: number; offset: number; has_more: boolean }
export interface CatalogueFacets { departments: string[]; categories: string[]; colors: string[]; price_min: number; price_max: number; total_products: number }

const colorHex = (name: string) => {
  const value = name.toLowerCase();
  if (value.includes('black')) return '#111111'; if (value.includes('white') || value.includes('ecru')) return '#f4f2eb';
  if (value.includes('blue') || value.includes('navy')) return '#355c7d'; if (value.includes('brown') || value.includes('camel')) return '#6b4636';
  if (value.includes('red') || value.includes('burgundy')) return '#8f2635'; if (value.includes('green') || value.includes('khaki')) return '#52634f';
  if (value.includes('pink')) return '#d6a7af'; if (value.includes('yellow')) return '#d3af47'; return '#777777';
};

export const toProduct = (item: ApiProduct): Product => {
  const matched = item.matched_variant;
  const matchedGallery = (matched?.gallery_urls || []).filter(Boolean);
  const images = Array.from(new Set([matched?.image_url, ...matchedGallery, ...(item.image_urls || [])].filter((value): value is string => Boolean(value))));
  const colorNames = Array.from(new Set([matched?.color, ...(item.colors || [])].filter((value): value is string => Boolean(value))));
  const matchedVariant = matched ? { id: matched.variant_id, sku: matched.sku || 'Information unavailable',
    size: matched.size || 'Information unavailable', color: matched.color || undefined,
    inStock: matched.in_stock, availabilityState: matched.availability_state,
    image: matched.image_url || undefined, gallery: matchedGallery, price: matched.price == null ? undefined : Number(matched.price) } : undefined;
  return {
  id: item.product_id, name: item.name || 'Information unavailable', price: matchedVariant?.price ?? (Number(item.price) || 0), originalPrice: item.original_price,
  currency: item.currency || 'USD', department: item.department || 'Collection', category: item.category || 'Information unavailable',
  description: item.description?.trim() || 'Information unavailable', longDescription: item.description?.trim() || 'Information unavailable', image: images[0] || '', gallery: images,
  colors: colorNames.map((name) => ({ name, hex: colorHex(name) })), sizes: (item.sizes || []).filter(Boolean),
  variants: matchedVariant ? [matchedVariant] : undefined, matchedVariant,
  inStock: matchedVariant?.inStock ?? item.available, isSale: item.is_on_sale, provenance: 'SOURCE_CATALOGUE_CDN',
  videoUrl: item.hero_video_url || undefined, modelWalkUrl: item.model_walk_url || undefined,
  lookbookMedia: item.lookbook_media || (item.hero_media_url ? [item.hero_media_url] : undefined),
  };
};

export const preserveMatchedVariant = (details: Product, result: Product): Product => {
  if (!result.matchedVariant) return details;
  const matched = result.matchedVariant;
  const colors = matched.color
    ? [details.colors.find((color) => color.name === matched.color) || { name: matched.color, hex: colorHex(matched.color) },
       ...details.colors.filter((color) => color.name !== matched.color)]
    : details.colors;
  const gallery = Array.from(new Set([matched.image, ...(matched.gallery || []), ...details.gallery].filter((value): value is string => Boolean(value))));
  return { ...details, matchedVariant: matched, variants: [matched, ...(details.variants || []).filter((item) => item.id !== matched.id)],
    colors, gallery, image: matched.image || details.image, price: matched.price ?? details.price, inStock: matched.inStock };
};

export const resolveProductImage = (product: Product, requested: string, failed: string[]) =>
  !failed.includes(requested) ? requested : product.gallery.find((image) => !failed.includes(image)) || '';

export async function fetchCatalogueProducts(filter: ProductFilter, limit = 24, offset = 0, signal?: AbortSignal) {
  const params = new URLSearchParams({ limit: String(limit), offset: String(offset), sort: ({ 'price-asc': 'price_low_high', 'price-desc': 'price_high_low' } as Record<string, string>)[filter.sort] || filter.sort });
  if (filter.searchQuery) params.set('q', filter.searchQuery); if (filter.category) params.set('category', filter.category);
  if (filter.department) params.set('department', filter.department); if (filter.color) params.set('color', filter.color);
  if (filter.minPrice !== undefined) params.set('min_price', String(filter.minPrice)); if (filter.maxPrice !== undefined) params.set('max_price', String(filter.maxPrice));
  if (filter.inStockOnly) params.set('available_only', 'true');
  const response = await fetch(`${API_URL}/v1/catalogue/products?${params}`, { signal });
  if (!response.ok) throw new Error(`Catalogue request failed (${response.status})`);
  const payload = await response.json() as ApiList;
  return { ...payload, items: payload.items.map(toProduct) };
}

export async function fetchCatalogueFacets(signal?: AbortSignal): Promise<CatalogueFacets> {
  const response = await fetch(`${API_URL}/v1/catalogue/facets`, { signal }); if (!response.ok) throw new Error('Facets unavailable'); return response.json();
}

export async function fetchStyledEdit(signal?: AbortSignal): Promise<Product[]> {
  const response = await fetch(`${API_URL}/v1/catalogue/styled-edit?limit=8`, { signal }); if (!response.ok) throw new Error('Styled edit unavailable');
  const payload = await response.json() as { items: ApiProduct[] }; return payload.items.map(toProduct);
}

export async function fetchProductDetails(productId: string): Promise<Product> {
  const response = await fetch(`${API_URL}/v1/catalogue/products/${encodeURIComponent(productId)}`); if (!response.ok) throw new Error('Product unavailable'); return toProduct(await response.json() as ApiProduct);
}
