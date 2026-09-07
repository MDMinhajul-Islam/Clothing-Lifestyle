import React from 'react';
import { Search, X, SlidersHorizontal, ArrowUpDown } from 'lucide-react';
import type { ProductFilter, SortOption } from '../../types/catalog';

interface FilterBarProps {
  filter: ProductFilter;
  onChangeFilter: (newFilter: ProductFilter) => void;
  onResetFilter: () => void;
  totalResults: number;
}

const CATEGORIES = [
  'All Items',
  'Dresses',
  'Blazers & Jackets',
  'Tops & Shirts',
  'Pants & Jeans',
  'Knitwear',
  'Shoes & Bags',
];

const OCCASIONS = ['All Occasions', 'Party', 'Workwear', 'Evening', 'Weekend', 'Cozy'];

const COLORS = [
  { name: 'All Colors', hex: '' },
  { name: 'Black', hex: '#111111' },
  { name: 'Ecru', hex: '#f5f4ef' },
  { name: 'Blue', hex: '#355c7d' },
  { name: 'Brown', hex: '#3d2314' },
  { name: 'Charcoal', hex: '#2d2d2d' },
];

export const FilterBar: React.FC<FilterBarProps> = ({
  filter,
  onChangeFilter,
  onResetFilter,
  totalResults,
}) => {
  const [showAdvanced, setShowAdvanced] = React.useState(false);

  const hasActiveFilters = Boolean(
    filter.category ||
    filter.occasion ||
    filter.department ||
    filter.color ||
    filter.searchQuery ||
    filter.maxPrice
  );

  return (
    <div className="border-b border-neutral-200 bg-white sticky top-20 z-30 transition-all">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-3">
        {/* Top Row: Search, Category Chips, Sort, Filter Toggle */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
          {/* Category Chips Carousel */}
          <div className="flex items-center space-x-2 overflow-x-auto pb-1 md:pb-0 no-scrollbar">
            {CATEGORIES.map((cat) => {
              const isSelected = (!filter.category && cat === 'All Items') || filter.category === cat;
              return (
                <button
                  key={cat}
                  onClick={() =>
                    onChangeFilter({
                      ...filter,
                      category: cat === 'All Items' ? undefined : cat,
                    })
                  }
                  className={`px-3 py-1.5 text-xs tracking-wider uppercase font-medium whitespace-nowrap transition-all rounded-none border ${
                    isSelected
                      ? 'bg-black text-white border-black'
                      : 'bg-neutral-50 text-neutral-600 border-neutral-200 hover:border-neutral-400 hover:bg-white'
                  }`}
                >
                  {cat}
                </button>
              );
            })}
          </div>

          {/* Right Controls: Search, Sort, Filter Drawer */}
          <div className="flex items-center space-x-3 self-end md:self-auto">
            {/* Search Box */}
            <div className="relative">
              <input
                type="text"
                placeholder="Search pieces..."
                value={filter.searchQuery || ''}
                onChange={(e) =>
                  onChangeFilter({
                    ...filter,
                    searchQuery: e.target.value || undefined,
                  })
                }
                className="w-40 sm:w-56 pl-8 pr-3 py-1.5 text-xs bg-neutral-50 border border-neutral-200 focus:bg-white focus:border-black focus:outline-none transition-all"
              />
              <Search className="w-3.5 h-3.5 text-neutral-400 absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
              {filter.searchQuery && (
                <button
                  onClick={() => onChangeFilter({ ...filter, searchQuery: undefined })}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-neutral-400 hover:text-black"
                >
                  <X className="w-3 h-3" />
                </button>
              )}
            </div>

            {/* Sort Dropdown */}
            <div className="relative flex items-center">
              <select
                value={filter.sort}
                onChange={(e) =>
                  onChangeFilter({ ...filter, sort: e.target.value as SortOption })
                }
                aria-label="Sort products by"
                className="text-xs tracking-wider uppercase font-medium bg-neutral-50 border border-neutral-200 px-2.5 py-1.5 pr-6 appearance-none focus:outline-none focus:border-black cursor-pointer"
              >
                <option value="featured">Featured</option>
                <option value="price-asc">Price: Low to High</option>
                <option value="price-desc">Price: High to Low</option>
                <option value="newest">New Arrivals</option>
              </select>
              <ArrowUpDown className="w-3 h-3 text-neutral-500 absolute right-2 pointer-events-none" />
            </div>

            {/* Filter Toggle */}
            <button
              onClick={() => setShowAdvanced(!showAdvanced)}
              className={`flex items-center space-x-1 px-3 py-1.5 text-xs uppercase tracking-wider font-medium border transition-colors ${
                showAdvanced || hasActiveFilters
                  ? 'bg-black text-white border-black'
                  : 'bg-neutral-50 text-neutral-700 border-neutral-200 hover:border-black'
              }`}
            >
              <SlidersHorizontal className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Filters</span>
            </button>
          </div>
        </div>

        {/* Advanced Filters Panel (Occasion, Color, Department) */}
        {showAdvanced && (
          <div className="mt-3 pt-3 border-t border-neutral-100 grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
            {/* Occasions */}
            <div>
              <span className="font-mono text-[10px] tracking-wider uppercase text-neutral-400 block mb-2">
                Occasion / Mood
              </span>
              <div className="flex flex-wrap gap-1.5">
                {OCCASIONS.map((occ) => {
                  const isSelected = (!filter.occasion && occ === 'All Occasions') || filter.occasion === occ;
                  return (
                    <button
                      key={occ}
                      onClick={() =>
                        onChangeFilter({
                          ...filter,
                          occasion: occ === 'All Occasions' ? undefined : occ,
                        })
                      }
                      className={`px-2.5 py-1 rounded-sm border ${
                        isSelected
                          ? 'bg-neutral-900 text-white border-neutral-900'
                          : 'bg-white text-neutral-600 border-neutral-200 hover:border-neutral-400'
                      }`}
                    >
                      {occ}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Color Palette */}
            <div>
              <span className="font-mono text-[10px] tracking-wider uppercase text-neutral-400 block mb-2">
                Color Shade
              </span>
              <div className="flex flex-wrap gap-2">
                {COLORS.map((col) => {
                  const isSelected = (!filter.color && col.name === 'All Colors') || filter.color === col.name;
                  return (
                    <button
                      key={col.name}
                      onClick={() =>
                        onChangeFilter({
                          ...filter,
                          color: col.name === 'All Colors' ? undefined : col.name,
                        })
                      }
                      className={`flex items-center space-x-1.5 px-2.5 py-1 rounded-sm border ${
                        isSelected
                          ? 'bg-neutral-900 text-white border-neutral-900'
                          : 'bg-white text-neutral-700 border-neutral-200 hover:border-neutral-400'
                      }`}
                    >
                      {col.hex && (
                        <span
                          className="w-2.5 h-2.5 rounded-full border border-neutral-300 inline-block"
                          style={{ backgroundColor: col.hex }}
                        />
                      )}
                      <span>{col.name}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Department */}
            <div>
              <span className="font-mono text-[10px] tracking-wider uppercase text-neutral-400 block mb-2">
                Department
              </span>
              <div className="flex gap-2">
                {['ALL', 'WOMAN', 'MAN'].map((dept) => {
                  const isSelected = (!filter.department && dept === 'ALL') || filter.department === dept;
                  return (
                    <button
                      key={dept}
                      onClick={() =>
                        onChangeFilter({
                          ...filter,
                          department: dept === 'ALL' ? undefined : dept,
                        })
                      }
                      className={`px-3 py-1 border ${
                        isSelected
                          ? 'bg-black text-white border-black'
                          : 'bg-white text-neutral-700 border-neutral-200 hover:border-neutral-400'
                      }`}
                    >
                      {dept}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {/* Active Filter Pills and Counts */}
        <div className="mt-2.5 flex items-center justify-between text-[11px] font-mono text-neutral-500">
          <div className="flex items-center space-x-2 flex-wrap gap-y-1">
            <span>Showing {totalResults} curated pieces</span>
            {hasActiveFilters && (
              <>
                <span className="text-neutral-300">•</span>
                <span className="text-neutral-900">Filtered by:</span>
                {filter.category && (
                  <span className="bg-neutral-100 text-neutral-800 px-1.5 py-0.5 rounded flex items-center gap-1">
                    {filter.category}
                    <X
                      className="w-2.5 h-2.5 cursor-pointer"
                      onClick={() => onChangeFilter({ ...filter, category: undefined })}
                    />
                  </span>
                )}
                {filter.color && (
                  <span className="bg-neutral-100 text-neutral-800 px-1.5 py-0.5 rounded flex items-center gap-1">
                    {filter.color}
                    <X
                      className="w-2.5 h-2.5 cursor-pointer"
                      onClick={() => onChangeFilter({ ...filter, color: undefined })}
                    />
                  </span>
                )}
                {filter.occasion && (
                  <span className="bg-neutral-100 text-neutral-800 px-1.5 py-0.5 rounded flex items-center gap-1">
                    {filter.occasion}
                    <X
                      className="w-2.5 h-2.5 cursor-pointer"
                      onClick={() => onChangeFilter({ ...filter, occasion: undefined })}
                    />
                  </span>
                )}
                {filter.searchQuery && (
                  <span className="bg-neutral-100 text-neutral-800 px-1.5 py-0.5 rounded flex items-center gap-1">
                    “{filter.searchQuery}”
                    <X
                      className="w-2.5 h-2.5 cursor-pointer"
                      onClick={() => onChangeFilter({ ...filter, searchQuery: undefined })}
                    />
                  </span>
                )}
                <button
                  onClick={onResetFilter}
                  className="text-neutral-900 underline hover:text-black ml-2"
                >
                  Reset all
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
