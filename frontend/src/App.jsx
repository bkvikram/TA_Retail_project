import { useCallback, useEffect, useState } from "react";
import { searchPricing } from "./api/client.js";
import PricingTable from "./components/PricingTable.jsx";
import SearchFilters from "./components/SearchFilters.jsx";
import UploadPanel from "./components/UploadPanel.jsx";

const PAGE_SIZE = 25;

export default function App() {
  const [filters, setFilters] = useState({});
  const [page, setPage] = useState(1);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const runSearch = useCallback(async (nextFilters, nextPage) => {
    setLoading(true);
    setError(null);
    try {
      const data = await searchPricing(nextFilters, nextPage, PAGE_SIZE);
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    runSearch(filters, page);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page]);

  const handleSearch = (nextFilters) => {
    setFilters(nextFilters);
    setPage(1);
    runSearch(nextFilters, 1);
  };

  const handleRecordUpdated = (updated) => {
    setResult((prev) => ({
      ...prev,
      items: prev.items.map((item) => (item.id === updated.id ? updated : item)),
    }));
  };

  return (
    <main className="app">
      <header>
        <h1>Retail Pricing Feed Manager</h1>
        <p className="hint">Upload store price feeds and manage pricing records across the chain.</p>
      </header>

      <UploadPanel onUploadComplete={() => runSearch(filters, page)} />
      <SearchFilters onSearch={handleSearch} />

      {loading && <p className="hint">Loading...</p>}
      {error && <p className="error">{error}</p>}

      <PricingTable
        page={page}
        pageSize={PAGE_SIZE}
        result={result}
        onPageChange={setPage}
        onRecordUpdated={handleRecordUpdated}
      />
    </main>
  );
}
