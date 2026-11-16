// IAOD REST API Client & Toast Helper

async function apiFetch(url, options = {}) {
  const defaultHeaders = {
    'Accept': 'application/json'
  };
  
  if (options.body && !(options.body instanceof FormData)) {
    defaultHeaders['Content-Type'] = 'application/json';
    if (typeof options.body !== 'string') {
      options.body = JSON.stringify(options.body);
    }
  }

  options.headers = { ...defaultHeaders, ...(options.headers || {}) };

  try {
    const res = await fetch(url, options);
    const contentType = res.headers.get('content-type');
    let data = null;
    if (contentType && contentType.includes('application/json')) {
      data = await res.json();
    } else {
      data = await res.text();
    }

    if (!res.ok) {
      const errMessage = (data && data.error) ? `${data.error}: ${data.details || data.message || ''}` : `HTTP Error ${res.status}`;
      throw new Error(errMessage);
    }
    return data;
  } catch (err) {
    console.error('API Error:', err);
    throw err;
  }
}

function showToast(message, type = 'info') {
  let toastContainer = document.getElementById('toast-container');
  if (!toastContainer) {
    toastContainer = document.createElement('div');
    toastContainer.id = 'toast-container';
    toastContainer.style.position = 'fixed';
    toastContainer.style.top = '20px';
    toastContainer.style.right = '20px';
    toastContainer.style.zIndex = '9999';
    toastContainer.style.display = 'flex';
    toastContainer.style.flexDirection = 'column';
    toastContainer.style.gap = '10px';
    document.body.appendChild(toastContainer);
  }

  const toast = document.createElement('div');
  const bg = type === 'error' ? '#ef4444' : (type === 'success' ? '#10b981' : '#2563eb');
  toast.style.backgroundColor = bg;
  toast.style.color = '#fff';
  toast.style.padding = '12px 20px';
  toast.style.borderRadius = '6px';
  toast.style.boxShadow = '0 4px 6px rgba(0,0,0,0.15)';
  toast.style.fontSize = '14px';
  toast.style.fontWeight = '500';
  toast.style.maxWidth = '360px';
  toast.style.transition = 'all 0.3s ease';
  toast.innerText = message;

  toastContainer.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(-10px)';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}
