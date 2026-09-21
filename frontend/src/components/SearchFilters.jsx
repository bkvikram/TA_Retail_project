import { useState } from "react";

const EMPTY_FILTERS = {
  store_id: "",
  sku: "",
  product_name: "",
  min_price: "",
  max_price: "",
  date_from: "",
  date_to: "",
};

export default function SearchFilters({ onSearch }) {
  const [filters, setFilters] = useState(EMPTY_FILTERS);

  const update = (field) => (event) => setFilters({ ...filters, [field]: event.target.value });

  const submit = (event) => {
    event.preventDefault();
    onSearch(filters);
  };

  const reset = () => {
    setFilters(EMPTY_FILTERS);
    onSearch(EMPTY_FILTERS);
  };

  return (
    <form className="panel filters" onSubmit={submit}>
      <h2>Search Pricing Records</h2>
      <div className="filter-grid">
        <label>
          Store ID
          <input value={filters.store_id} onChange={update("store_id")} placeholder="e.g. ST001" />
        </label>
        <label>
          SKU
          <input value={filters.sku} onChange={update("sku")} placeholder="e.g. SKU100" />
        </label>
        <label>
          Product Name
          <input value={filters.product_name} onChange={update("product_name")} placeholder="contains..." />
        </label>
        <label>
          Min Price
          <input type="number" step="0.01" min="0" value={filters.min_price} onChange={update("min_price")} />
        </label>
        <label>
          Max Price
          <input type="number" step="0.01" min="0" value={filters.max_price} onChange={update("max_price")} />
        </label>
        <label>
          Date From
          <input type="date" value={filters.date_from} onChange={update("date_from")} />
        </label>
        <label>
          Date To
          <input type="date" value={filters.date_to} onChange={update("date_to")} />
        </label>
      </div>
      <div className="filter-actions">
        <button type="submit">Search</button>
        <button type="button" className="secondary" onClick={reset}>
          Clear
        </button>
      </div>
    </form>
  );
}
