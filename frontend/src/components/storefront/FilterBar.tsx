import React from 'react';
import { ArrowUpDown, Search, SlidersHorizontal, Sparkles, X } from 'lucide-react';
import type { ProductFilter, SortOption } from '../../types/catalog';

interface FilterBarProps {
  filter: ProductFilter;
  onChangeFilter: (filter: ProductFilter) => void;
  onResetFilter: () => void;
  totalResults: number;
  totalCatalogueCount?: number;
  activeVoiceFilterLabel?: string | null;
  onClearVoiceFilter?: () => void;
  availableColors?: Array<{ name: string; hex: string }>;
  availableCategories?: string[];
  availableDepartments?: string[];
}

const CATEGORIES = ['All Items', 'Dresses', 'Blazers & Jackets', 'Tops & Shirts', 'Pants & Jeans', 'Knitwear', 'Shoes & Bags'];
const DEPARTMENTS = ['All', 'WOMAN', 'MAN', 'UNISEX'];
const PRICE_PRESETS = [{ label: 'Under $50', maxPrice: 50 }, { label: 'Under $100', maxPrice: 100 }, { label: '$100–$200', minPrice: 100, maxPrice: 200 }, { label: '$200+', minPrice: 200 }];

export const FilterBar: React.FC<FilterBarProps> = ({ filter, onChangeFilter, onResetFilter, totalResults, totalCatalogueCount = 6018, activeVoiceFilterLabel, onClearVoiceFilter, availableColors = [], availableCategories = CATEGORIES.slice(1), availableDepartments = DEPARTMENTS.slice(1) }) => {
  const [expanded, setExpanded] = React.useState(false);
  const active = Boolean(filter.category || filter.department || filter.color || filter.searchQuery || filter.minPrice !== undefined || filter.maxPrice !== undefined || filter.inStockOnly);
  const update = (patch: Partial<ProductFilter>) => onChangeFilter({ ...filter, ...patch });

  return (
    <div className="sticky top-20 z-30 border-b border-neutral-200 bg-white/95 backdrop-blur-xl">
      <div className="mx-auto max-w-[1600px] px-4 py-4 sm:px-8 lg:px-12 2xl:px-16">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
          <div className="flex gap-2 overflow-x-auto pb-1">
            {['All Items', ...availableCategories].map((category) => {
              const selected = category === 'All Items' ? !filter.category : filter.category === category;
              return <button key={category} onClick={() => update({ category: category === 'All Items' ? undefined : category })} className={`whitespace-nowrap border px-3.5 py-2 text-[10px] font-semibold uppercase tracking-[0.14em] ${selected ? 'border-black bg-black text-white' : 'border-neutral-200 bg-neutral-50 text-neutral-600 hover:border-black'}`}>{category}</button>;
            })}
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <label className="relative flex-1 sm:flex-none">
              <Search className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-neutral-400" />
              <input value={filter.searchQuery || ''} onChange={(event) => update({ searchQuery: event.target.value || undefined })} placeholder="Search the collection" className="w-full border border-neutral-200 bg-neutral-50 py-2 pl-9 pr-8 text-xs outline-none focus:border-black sm:w-64" />
              {filter.searchQuery && <button onClick={() => update({ searchQuery: undefined })} className="absolute right-2.5 top-1/2 -translate-y-1/2"><X className="h-3 w-3" /></button>}
            </label>
            <label className="flex items-center gap-2 border border-neutral-200 bg-neutral-50 px-3 py-2 text-[10px] uppercase tracking-wider">
              <ArrowUpDown className="h-3.5 w-3.5" />
              <select value={filter.sort} onChange={(event) => update({ sort: event.target.value as SortOption })} className="bg-transparent outline-none">
                <option value="featured">Featured</option><option value="newest">New arrivals</option><option value="price-asc">Price low-high</option><option value="price-desc">Price high-low</option>
              </select>
            </label>
            <button onClick={() => setExpanded((value) => !value)} className={`flex items-center gap-2 border px-3 py-2 text-[10px] font-semibold uppercase tracking-wider ${expanded || active ? 'border-black bg-black text-white' : 'border-neutral-200 bg-neutral-50'}`}><SlidersHorizontal className="h-3.5 w-3.5" />Filters</button>
          </div>
        </div>

        <div className="mt-3 flex flex-col gap-3 border-t border-neutral-100 pt-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex flex-wrap items-center gap-2 text-[10px] uppercase tracking-wider text-neutral-500">
            <span><strong className="text-neutral-900">{totalResults}</strong> preview pieces shown · connected catalogue {totalCatalogueCount.toLocaleString()}</span>
            {activeVoiceFilterLabel && <span className="inline-flex items-center gap-1.5 bg-neutral-900 px-2.5 py-1 text-white"><Sparkles className="h-3 w-3 text-emerald-400" />AI curated: {activeVoiceFilterLabel}<button onClick={onClearVoiceFilter} aria-label="Clear voice selection"><X className="h-3 w-3" /></button></span>}
            {active && <button onClick={onResetFilter} className="underline hover:text-black">Clear all</button>}
          </div>
          <div className="flex gap-3 text-[10px] font-semibold uppercase tracking-wider text-neutral-500">
            {['All', ...availableDepartments].map((department) => <button key={department} onClick={() => update({ department: department === 'All' ? undefined : department })} className={(department === 'All' ? !filter.department : filter.department === department) ? 'border-b border-black text-black' : 'hover:text-black'}>{department}</button>)}
          </div>
        </div>

        {expanded && (
          <div className="mt-4 grid gap-6 border-t border-neutral-200 pt-4 lg:grid-cols-[1.3fr_1.3fr_0.7fr]">
            <div><span className="mb-2 block text-[10px] uppercase tracking-widest text-neutral-500">Color</span><div className="flex max-h-24 flex-wrap gap-2 overflow-y-auto"><button onClick={() => update({ color: undefined })} className={`border px-2.5 py-1.5 text-xs ${!filter.color ? 'border-black bg-black text-white' : 'border-neutral-200'}`}>All colors</button>{availableColors.map(({ name, hex }) => <button key={name} onClick={() => update({ color: name })} className={`flex items-center gap-1.5 border px-2.5 py-1.5 text-xs ${filter.color === name ? 'border-black' : 'border-neutral-200'}`}><span className="h-2.5 w-2.5 rounded-full border border-black/20" style={{ backgroundColor: hex }} />{name}</button>)}</div></div>
            <div><span className="mb-2 block text-[10px] uppercase tracking-widest text-neutral-500">Price</span><div className="flex flex-wrap gap-2">{PRICE_PRESETS.map((preset) => <button key={preset.label} onClick={() => update({ minPrice: preset.minPrice, maxPrice: preset.maxPrice })} className={`border px-2.5 py-1.5 text-xs ${filter.minPrice === preset.minPrice && filter.maxPrice === preset.maxPrice ? 'border-black bg-black text-white' : 'border-neutral-200'}`}>{preset.label}</button>)}</div><div className="mt-2 flex items-center gap-2"><label className="flex items-center border border-neutral-200 px-2 text-xs text-neutral-400">$<input type="number" min="0" value={filter.minPrice ?? ''} onChange={(event) => update({ minPrice: event.target.value ? Number(event.target.value) : undefined })} placeholder="Min" className="w-16 px-1 py-2 text-neutral-900 outline-none" /></label><span className="text-neutral-300">—</span><label className="flex items-center border border-neutral-200 px-2 text-xs text-neutral-400">$<input type="number" min="0" value={filter.maxPrice ?? ''} onChange={(event) => update({ maxPrice: event.target.value ? Number(event.target.value) : undefined })} placeholder="Max" className="w-16 px-1 py-2 text-neutral-900 outline-none" /></label></div></div>
            <label className="flex items-center gap-2 text-xs text-neutral-700"><input type="checkbox" checked={Boolean(filter.inStockOnly)} onChange={(event) => update({ inStockOnly: event.target.checked })} className="accent-black" />Available pieces only</label>
          </div>
        )}
      </div>
    </div>
  );
};
