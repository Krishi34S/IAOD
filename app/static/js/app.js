// IAOD Main Application Logic

document.addEventListener('DOMContentLoaded', () => {
  initTabs();
  initFileUpload();
  initManualInvoiceBuilder();
});

// 1. Tab Switching
function initTabs() {
  const tabs = document.querySelectorAll('.tab-btn');
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      const targetId = tab.dataset.target;
      document.querySelectorAll('.tab-btn').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
      
      tab.classList.add('active');
      const targetContent = document.getElementById(targetId);
      if (targetContent) targetContent.classList.add('active');
    });
  });
}

// 2. File Upload Handling
function initFileUpload() {
  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('file-input');
  if (!dropzone || !fileInput) return;

  ['dragenter', 'dragover'].forEach(eventName => {
    dropzone.addEventListener(eventName, e => {
      e.preventDefault();
      dropzone.classList.add('dragover');
    });
  });

  ['dragleave', 'drop'].forEach(eventName => {
    dropzone.addEventListener(eventName, e => {
      e.preventDefault();
      dropzone.classList.remove('dragover');
    });
  });

  dropzone.addEventListener('drop', e => {
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileSelected(e.dataTransfer.files[0]);
    }
  });

  fileInput.addEventListener('change', e => {
    if (e.target.files && e.target.files.length > 0) {
      handleFileSelected(e.target.files[0]);
    }
  });
}

async function handleFileSelected(file) {
  const statusDiv = document.getElementById('upload-status');
  if (statusDiv) {
    statusDiv.style.display = 'block';
    statusDiv.innerHTML = `<span style="color:#2563eb">Uploading and analyzing <b>${file.name}</b>...</span>`;
  }

  const formData = new FormData();
  formData.append('file', file);

  try {
    const res = await fetch('/api/invoices', {
      method: 'POST',
      body: formData
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.details || data.error || 'Failed to process file');
    }
    showToast(`Invoice analyzed! Status: ${data.status} (Anomalies: ${data.total_anomalies})`, data.status === 'NORMAL' ? 'success' : 'error');
    setTimeout(() => {
      window.location.href = `/invoices/${data.invoice_id}`;
    }, 1000);
  } catch (err) {
    if (statusDiv) {
      statusDiv.innerHTML = `<span style="color:#ef4444">Error: ${err.message}</span>`;
    }
    showToast(err.message, 'error');
  }
}

// 3. Manual Invoice Builder
function initManualInvoiceBuilder() {
  const addItemBtn = document.getElementById('btn-add-item');
  const itemsContainer = document.getElementById('items-tbody');
  const manualForm = document.getElementById('manual-invoice-form');

  if (!manualForm) return;

  if (addItemBtn) {
    addItemBtn.addEventListener('click', () => {
      addManualItemRow();
    });
  }

  manualForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    submitManualInvoice();
  });

  // Attach live calculation listeners
  recalculateTotals();
}

function addManualItemRow(desc = '', category = 'General', qty = 1, price = 0, lineTotal = 0) {
  const tbody = document.getElementById('items-tbody');
  if (!tbody) return;

  const row = document.createElement('tr');
  row.className = 'item-row';
  row.innerHTML = `
    <td>
      <input type="text" class="form-control item-desc" placeholder="e.g. Dell Laptop" value="${desc}" required list="ref-items-datalist">
    </td>
    <td>
      <input type="text" class="form-control item-cat" placeholder="Category" value="${category}">
    </td>
    <td style="width: 100px;">
      <input type="number" step="0.01" min="0.01" class="form-control item-qty" value="${qty}" required>
    </td>
    <td style="width: 140px;">
      <input type="number" step="0.01" min="0" class="form-control item-price" value="${price}" required>
    </td>
    <td style="width: 150px;">
      <input type="number" step="0.01" min="0" class="form-control item-line-total" value="${lineTotal}">
    </td>
    <td style="width: 50px; text-align: center;">
      <button type="button" class="btn btn-sm btn-danger btn-remove-item">&times;</button>
    </td>
  `;

  tbody.appendChild(row);

  // Attach inputs recalculation
  const inputs = row.querySelectorAll('input');
  inputs.forEach(input => {
    input.addEventListener('input', (e) => {
      if (input.classList.contains('item-qty') || input.classList.contains('item-price')) {
        const q = parseFloat(row.querySelector('.item-qty').value) || 0;
        const p = parseFloat(row.querySelector('.item-price').value) || 0;
        row.querySelector('.item-line-total').value = (q * p).toFixed(2);
      }
      recalculateTotals();
    });
  });

  row.querySelector('.btn-remove-item').addEventListener('click', () => {
    if (document.querySelectorAll('.item-row').length > 1) {
      row.remove();
      recalculateTotals();
    } else {
      showToast('Invoice must have at least one line item', 'error');
    }
  });

  recalculateTotals();
}

function recalculateTotals() {
  const rows = document.querySelectorAll('.item-row');
  let expectedSubtotal = 0;
  let billedSubtotal = 0;

  rows.forEach(row => {
    const q = parseFloat(row.querySelector('.item-qty')?.value) || 0;
    const p = parseFloat(row.querySelector('.item-price')?.value) || 0;
    const lt = parseFloat(row.querySelector('.item-line-total')?.value) || 0;
    
    expectedSubtotal += (q * p);
    billedSubtotal += lt;
  });

  const taxRate = parseFloat(document.getElementById('tax_rate')?.value) || 0;
  const discount = parseFloat(document.getElementById('discount_amount')?.value) || 0;
  
  const expectedTax = Math.max(0, (expectedSubtotal - discount) * (taxRate / 100));
  const expectedTotal = Math.max(0, expectedSubtotal - discount + expectedTax);

  // Update display preview elements
  const expSubElem = document.getElementById('preview-expected-subtotal');
  const expTaxElem = document.getElementById('preview-expected-tax');
  const expTotElem = document.getElementById('preview-expected-total');

  if (expSubElem) expSubElem.innerText = expectedSubtotal.toFixed(2);
  if (expTaxElem) expTaxElem.innerText = expectedTax.toFixed(2);
  if (expTotElem) expTotElem.innerText = expectedTotal.toFixed(2);

  // Update Billed Total field if not manually overridden
  const billedTotalInput = document.getElementById('billed_total');
  if (billedTotalInput && !billedTotalInput.dataset.manualOverride) {
    const billedTax = parseFloat(document.getElementById('tax_amount')?.value) || expectedTax;
    billedTotalInput.value = (billedSubtotal - discount + billedTax).toFixed(2);
  }
}

async function submitManualInvoice() {
  const invoiceNumber = document.getElementById('invoice_number').value.trim();
  const vendor = document.getElementById('vendor').value.trim();
  const invoiceDate = document.getElementById('invoice_date').value.trim();
  const taxRate = parseFloat(document.getElementById('tax_rate').value) || 0;
  const taxAmount = parseFloat(document.getElementById('tax_amount').value) || 0;
  const discountAmount = parseFloat(document.getElementById('discount_amount').value) || 0;
  const billedTotal = parseFloat(document.getElementById('billed_total').value) || 0;

  const rows = document.querySelectorAll('.item-row');
  const items = [];
  rows.forEach(r => {
    items.push({
      description: r.querySelector('.item-desc').value.trim(),
      category: r.querySelector('.item-cat').value.trim() || 'General',
      quantity: parseFloat(r.querySelector('.item-qty').value) || 0,
      unit_price: parseFloat(r.querySelector('.item-price').value) || 0,
      line_total: parseFloat(r.querySelector('.item-line-total').value) || 0
    });
  });

  const payload = {
    invoice_number: invoiceNumber,
    vendor: vendor,
    invoice_date: invoiceDate,
    tax_rate: taxRate,
    tax_amount: taxAmount,
    discount_amount: discountAmount,
    billed_total: billedTotal,
    items: items
  };

  try {
    const res = await apiFetch('/api/invoices', {
      method: 'POST',
      body: payload
    });
    showToast(`Invoice analyzed! Status: ${res.status}`, res.status === 'NORMAL' ? 'success' : 'error');
    setTimeout(() => {
      window.location.href = `/invoices/${res.invoice_id}`;
    }, 1000);
  } catch (err) {
    showToast(err.message, 'error');
  }
}
