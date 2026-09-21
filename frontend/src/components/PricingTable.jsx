import { useState } from "react";
import { updatePricingRecord } from "../api/client.js";

function EditableRow({ record, onSaved }) {
  const [editing, setEditing] = useState(false);
  const [productName, setProductName] = useState(record.product_name);
  const [price, setPrice] = useState(record.price);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const startEdit = () => {
    setProductName(record.product_name);
    setPrice(record.price);
    setError(null);
    setEditing(true);
  };

  const cancel = () => setEditing(false);

  const save = async () => {
    setSaving(true);
    setError(null);
    try {
      const changes = {};
      if (productName !== record.product_name) changes.product_name = productName;
      if (String(price) !== String(record.price)) changes.price = Number(price);
      const updated = Object.keys(changes).length ? await updatePricingRecord(record.id, changes) : record;
      onSaved(updated);
      setEditing(false);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <tr>
      <td>{record.store_id}</td>
      <td>{record.sku}</td>
      <td>
        {editing ? (
          <input value={productName} onChange={(e) => setProductName(e.target.value)} />
        ) : (
          record.product_name
        )}
      </td>
      <td>
        {editing ? (
          <input type="number" step="0.01" min="0" value={price} onChange={(e) => setPrice(e.target.value)} />
        ) : (
          `$${Number(record.price).toFixed(2)}`
        )}
      </td>
      <td>{record.price_date}</td>
      <td>{new Date(record.updated_at).toLocaleString()}</td>
      <td>{record.updated_by || "-"}</td>
      <td className="actions">
        {editing ? (
          <>
            <button onClick={save} disabled={saving}>
              {saving ? "Saving..." : "Save"}
            </button>
            <button className="secondary" onClick={cancel} disabled={saving}>
              Cancel
            </button>
          </>
        ) : (
          <button onClick={startEdit}>Edit</button>
        )}
        {error && <p className="error small">{error}</p>}
      </td>
    </tr>
  );
}

export default function PricingTable({ page, pageSize, result, onPageChange, onRecordUpdated }) {
  if (!result) return null;

  const totalPages = Math.max(1, Math.ceil(result.total / pageSize));

  return (
    <section className="panel">
      <h2>
        Results <span className="hint">({result.total} records)</span>
      </h2>
      <table>
        <thead>
          <tr>
            <th>Store ID</th>
            <th>SKU</th>
            <th>Product Name</th>
            <th>Price</th>
            <th>Price Date</th>
            <th>Last Updated</th>
            <th>Updated By</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {result.items.map((record) => (
            <EditableRow key={record.id} record={record} onSaved={onRecordUpdated} />
          ))}
          {result.items.length === 0 && (
            <tr>
              <td colSpan={8} className="empty">
                No records match the current filters.
              </td>
            </tr>
          )}
        </tbody>
      </table>

      <div className="pagination">
        <button disabled={page <= 1} onClick={() => onPageChange(page - 1)}>
          Previous
        </button>
        <span>
          Page {page} of {totalPages}
        </span>
        <button disabled={page >= totalPages} onClick={() => onPageChange(page + 1)}>
          Next
        </button>
      </div>
    </section>
  );
}
