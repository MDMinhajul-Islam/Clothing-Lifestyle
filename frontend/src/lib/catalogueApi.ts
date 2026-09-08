import type { Product, ProductFilter } from '../types/catalog';

const API_URL = (import.meta.env.VITE_BACKEND_API_URL || 'http://localhost:8000').replace(/\/$/, '');

interface ApiProduct { product_id: string; name: string; department: string; category?: string | null; description?: string | null; price: number; original_price?: number | null; currency: string; colors: string[]; sizes: string[]; image_urls: string[]; available: boolean; is_on_sale: boolean; hero_video_url?: string | null; hero_media_url?: string | null; model_walk_url?: string | null; lookbook_media?: string[] | null }
interface ApiList { items: ApiProduct[]; total: number; limit: number; offset: number; has_more: boolean }
export interface CatalogueFacets { departments: string[]; categories: string[]; colors: string[]; price_min: number; price_max: number; total_products: number }

const colorHex = (name: string) => {
  const value = name.toLowerCase();
  if (value.includes('black')) return '#111111'; if (value.includes('white') || value.includes('ecru')) return '#f4f2eb';
  if (value.includes('blue') || value.includes('navy')) return '#355c7d'; if (value.includes('brown') || value.includes('camel')) return '#6b4636';
  if (value.includes('red') || value.includes('burgundy')) return '#8f2635'; if (value.includes('green') || value.includes('khaki')) return '#52634f';
  if (value.includes('pink')) return '#d6a7af'; if (value.includes('yellow')) return '#d3af47'; return '#777777';
};

export const toProduct = (item: ApiProduct): Product => ({
  id: item.product_id, name: item.name, price: item.price, originalPrice: item.original_price,
  currency: item.currency, department: item.department, category: item.category || 'Collection',
  description: item.description || '', longDescription: item.description || '', image: item.image_urls[0] || '', gallery: item.image_urls,
  colors: item.colors.map((name) => ({ name, hex: colorHex(name) })), sizes: item.sizes,
  inStock: item.available, isSale: item.is_on_sale, provenance: 'SOURCE_CATALOGUE_CDN',
  videoUrl: item.hero_video_url || undefined, modelWalkUrl: item.model_walk_url || undefined,
  lookbookMedia: item.lookbook_media || (item.hero_media_url ? [item.hero_media_url] : undefined),
});

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
