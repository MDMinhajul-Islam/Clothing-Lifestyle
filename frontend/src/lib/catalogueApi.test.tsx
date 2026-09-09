import { renderToStaticMarkup } from 'react-dom/server';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { ProductCard } from '../components/storefront/ProductCard';
import { preserveMatchedVariant, resolveProductImage, toProduct } from './catalogueApi';
import { createRetellWebCall } from './api';

afterEach(() => vi.unstubAllGlobals());

const response = {
  product_id: 'zara-us:00264719', name: 'COMBINED STRAP DRESS', department: 'WOMAN',
  category: 'Dresses', description: 'A dress.', price: 49.9, currency: 'USD',
  colors: ['Dark khaki', 'Black'], sizes: ['S', 'M'],
  image_urls: ['https://example.test/default-khaki.jpg'], available: true, is_on_sale: false,
  matched_variant: { variant_id: 'black-m', sku: 'BLACK-M', color: 'Black', size: 'M',
    availability_state: 'IN_STOCK', in_stock: true,
    image_url: 'https://example.test/black.jpg',
    gallery_urls: ['https://example.test/black.jpg', 'https://example.test/black-detail.jpg'], price: 49.9 },
};

describe('variant-aware catalogue rendering', () => {
  it('maps the matching variant ahead of the default product media', () => {
    const product = toProduct(response);
    expect(product.image).toBe('https://example.test/black.jpg');
    expect(product.colors[0].name).toBe('Black');
    expect(product.matchedVariant?.sku).toBe('BLACK-M');
    expect(product.gallery.slice(0, 2)).toEqual([
      'https://example.test/black.jpg', 'https://example.test/black-detail.jpg',
    ]);
    expect(product.inStock).toBe(true);
  });

  it('renders the matching black image and color on the product card', () => {
    const markup = renderToStaticMarkup(<ProductCard product={toProduct(response)} onSelect={() => undefined} />);
    expect(markup).toContain('src="https://example.test/black.jpg"');
    expect(markup).toContain('>Black</span>');
  });

  it('preserves the search-selected variant after loading product details', () => {
    const result = toProduct(response);
    const details = toProduct({ ...response, matched_variant: null,
      image_urls: ['https://example.test/default-khaki.jpg'] });
    const merged = preserveMatchedVariant(details, result);
    expect(merged.image).toBe('https://example.test/black.jpg');
    expect(merged.matchedVariant?.sku).toBe('BLACK-M');
    expect(merged.colors[0].name).toBe('Black');
  });

  it('falls back to the next gallery image when variant media fails', () => {
    const product = toProduct(response);
    expect(resolveProductImage(product, product.image, [product.image]))
      .toBe('https://example.test/black-detail.jpg');
    expect(resolveProductImage(product, product.image, product.gallery)).toBe('');
  });
});

describe('voice product context', () => {
  it('sends the canonical product and matched variant when creating a Retell call', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({
      call_id: 'call-1', access_token: 'public-token',
    }) });
    vi.stubGlobal('fetch', fetchMock);
    await createRetellWebCall(undefined, {
      product_id: response.product_id,
      reference_product_id: response.product_id,
      active_variant_id: response.matched_variant.variant_id,
      sku: response.matched_variant.sku,
      color: response.matched_variant.color,
      size: response.matched_variant.size,
    });
    const request = fetchMock.mock.calls[0][1] as RequestInit;
    expect(JSON.parse(String(request.body))).toMatchObject({ context: {
      product_id: response.product_id,
      active_variant_id: 'black-m', sku: 'BLACK-M', color: 'Black', size: 'M',
    } });
  });
});
