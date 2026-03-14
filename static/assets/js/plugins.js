function loadScript(src) {
  const script = document.createElement('script');
  script.src = src;
  script.type = 'text/javascript';
  script.defer = true;
  document.head.appendChild(script);
}

// Verificar elementos y cargar los scripts necesarios
if (document.querySelectorAll("[toast-list]").length > 0 || 
  document.querySelectorAll('[data-choices]').length > 0 || 
  document.querySelectorAll("[data-provider]").length > 0) {
  
  loadScript('/static/assets/libs/toastify-js/toastify-js.min.js');
  loadScript('/static/assets/libs/choices.js/public/assets/scripts/choices.min.js');
  loadScript('/static/assets/libs/flatpickr/flatpickr.min.js');
}
