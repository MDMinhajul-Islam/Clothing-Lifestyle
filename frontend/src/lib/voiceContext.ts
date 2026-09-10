import type { Product } from '../types/catalog';
import type { WebpageVoiceContext } from '../types/voice';

export const buildWebpageVoiceContext = (
  activeProduct: Product | null,
  visibleProducts: Product[],
  query: string | undefined,
  pageUrl: string,
): WebpageVoiceContext => {
  const matched = activeProduct?.matchedVariant;
  return {
    product_id: activeProduct?.id,
    reference_product_id: activeProduct?.id,
    active_variant_id: matched?.id,
    product_reference: activeProduct?.commercialReference,
    sku: matched?.sku,
    color: matched?.color,
    size: matched?.size,
    query,
    page_url: pageUrl,
    visible_products: visibleProducts.slice(0, 10).map((product) => ({
      product_id: product.id,
      name: product.name,
      variant_id: product.matchedVariant?.id,
      sku: product.matchedVariant?.sku,
      color: product.matchedVariant?.color,
      size: product.matchedVariant?.size,
    })),
  };
};
