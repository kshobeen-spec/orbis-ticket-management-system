document.addEventListener('DOMContentLoaded', function(){
  try {
    // find change list table
    var table = document.querySelector('.change-list table');
    if(!table) return;
    var thead = table.querySelector('thead');
    var headers = thead.querySelectorAll('th');
    var statusIndex = -1;
    headers.forEach(function(h, idx){
      var text = h.textContent.trim().toLowerCase();
      if(text === 'status' || text === 'status '){ statusIndex = idx; }
    });
    if(statusIndex === -1) return;
    var rows = table.querySelectorAll('tbody tr');
    rows.forEach(function(r){
      var tds = r.querySelectorAll('td');
      if(tds.length <= statusIndex) return;
      var td = tds[statusIndex];
      var inner = td.textContent.trim();
      if(!inner) return;
      var key = inner.toLowerCase().replace(/\s+/g, '_');
      var span = document.createElement('span');
      span.className = 'badge-status badge-' + key;
      span.textContent = inner;
      td.innerHTML = '';
      td.appendChild(span);
    });
  } catch (e) {
    // fail silently
    console.warn('admin_custom.js error', e);
  }
});
