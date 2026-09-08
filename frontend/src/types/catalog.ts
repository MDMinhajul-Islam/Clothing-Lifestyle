export interface ProductColor {
  name: string;
  hex: string;
  code?: string;
}

export interface ProductVariant {
  id: string;
  size: string;
  sku: string;
  inStock: boolean;
  stockQuantity?: number;
}

export interface Product {
  id: string;
  name: string;
  price: number;
  originalPrice?: number | null;
  currency: string;
  department: 'WOMAN' | 'MAN' | 'KIDS' | 'UNISEX' | string;
  category: string;
  occasion?: string[];
  description: string;
  longDescription?: string;
  composition?: string;
  care?: string;
  fit?: string;
  image: string;
  gallery: string[];
  colors: ProductColor[];
  sizes: string[];
  variants?: ProductVariant[];
  inStock: boolean;
  isNew?: boolean;
  isSale?: boolean;
  commercialReference?: string;
  provenance: 'REFERENCE_SOURCE_CDN' | 'SOURCE_CATALOGUE_CDN';
  matchingProductIds?: string[];
  videoUrl?: string;
  modelWalkUrl?: string;
  lookbookMedia?: string[];
  variantMedia?: Record<string, string[]>;
}

export type SortOption = 'featured' | 'price-asc' | 'price-desc' | 'newest';

export interface ProductFilter {
  department?: string;
  category?: string;
  occasion?: string;
  searchQuery?: string;
  minPrice?: number;
  maxPrice?: number;
  color?: string;
  size?: string;
  inStockOnly?: boolean;
  sort: SortOption;
}

export interface OutfitRecommendation {
  title: string;
  occasion: string;
  editorialNote: string;
  items: Product[];
}
