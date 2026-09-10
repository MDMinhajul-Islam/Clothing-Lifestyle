import { describe, expect, it } from 'vitest';
import { buildWebpageVoiceContext } from './voiceContext';
import type { Product } from '../types/catalog';

const product = {
  id: 'product-1',
  name: 'Tailored Shirt',
  commercialReference: 'REF-1',
  matchedVariant: {
    id: 'variant-black-m',
    sku: 'SKU-BLACK-M',
    color: 'Black',
    size: 'M',
  },
} as Product;

describe('buildWebpageVoiceContext', () => {
  it('preserves the canonical active product and matched variant', () => {
    const context = buildWebpageVoiceContext(product, [product], 'black shirt', 'https://shop.example/product-1');
    expect(context).toMatchObject({
      product_id: 'product-1',
      reference_product_id: 'product-1',
      active_variant_id: 'variant-black-m',
      product_reference: 'REF-1',
      sku: 'SKU-BLACK-M',
      color: 'Black',
      size: 'M',
      query: 'black shirt',
      page_url: 'https://shop.example/product-1',
    });
    expect(context.visible_products?.[0]).toMatchObject({
      product_id: 'product-1',
      variant_id: 'variant-black-m',
      sku: 'SKU-BLACK-M',
      color: 'Black',
      size: 'M',
    });
  });

  it('keeps ordered search results when voice starts without an active product', () => {
    const second = { ...product, id: 'product-2', name: 'Second Shirt' } as Product;
    const context = buildWebpageVoiceContext(null, [product, second], 'office shirts', 'https://shop.example/');
    expect(context.reference_product_id).toBeUndefined();
    expect(context.visible_products?.map((item) => item.product_id)).toEqual(['product-1', 'product-2']);
  });
});
