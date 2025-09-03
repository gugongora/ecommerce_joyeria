// static/js/main.js
(() => {
  const $ = (sel, ctx = document) => ctx.querySelector(sel);
  const $$ = (sel, ctx = document) => Array.from(ctx.querySelectorAll(sel));

  const body = document.body;
  const API_BASE_URL = body.dataset.apiBaseUrl || '';

  // Utils
  const on = (el, ev, fn, opts) => el && el.addEventListener(ev, fn, opts);
  const delegate = (root, ev, selector, handler) => {
    on(root, ev, (e) => {
      const t = e.target.closest(selector);
      if (t && root.contains(t)) handler(e, t);
    });
  };

  // ---- Flash messages
  delegate(document, 'click', '[data-action="close-flash"]', (e, btn) => {
    const card = btn.closest('.relative');
    if (card) card.remove();
  });

  // ---- Modales (genéricos)
  delegate(document, 'click', '[data-modal-target]', (e, btn) => {
    const id = btn.getAttribute('data-modal-target');
    const el = document.getElementById(id);
    if (el) el.classList.remove('hidden');
  });
  delegate(document, 'click', '[data-modal-close]', (e, btn) => {
    const wrap = btn.closest('.fixed');
    if (wrap) wrap.classList.add('hidden');
  });

  // ---- Carrito
  const cartOverlay  = $('#cartOverlay');
  const cartSidebar  = $('#cartSidebar');
  const whatsappBtn  = $('#whatsappButton');

  function openCart() {
    if (!cartOverlay || !cartSidebar) return;
    cartOverlay.classList.remove('hidden');
    cartSidebar.classList.remove('translate-x-full');
    if (whatsappBtn) whatsappBtn.classList.add('hidden');
  }
  function closeCart() {
    if (!cartOverlay || !cartSidebar) return;
    cartSidebar.classList.add('translate-x-full');
    setTimeout(() => {
      cartOverlay.classList.add('hidden');
      if (whatsappBtn) whatsappBtn.classList.remove('hidden');
    }, 300);
  }

  delegate(document, 'click', '[data-action="open-cart"]', openCart);
  delegate(document, 'click', '[data-action="close-cart"]', closeCart);

  // Cerrar si clic fuera del sidebar
  on(cartOverlay, 'click', (e) => {
    if (!cartSidebar.contains(e.target)) closeCart();
  });

  // ---- Menú usuario
  (function userMenu() {
    const toggleBtns = $$('[data-action="toggle-user-menu"]');
    const menu   = $('#userDropdown');
    const group  = $('#userMenu');
    if (!toggleBtns.length || !menu || !group) return;

    const open = () => {
      menu.classList.remove('opacity-0','-translate-y-2','pointer-events-none');
      menu.classList.add('opacity-100','translate-y-0');
      toggleBtns.forEach(b => b.setAttribute('aria-expanded','true'));
    };
    const close = () => {
      menu.classList.add('opacity-0','-translate-y-2','pointer-events-none');
      menu.classList.remove('opacity-100','translate-y-0');
      toggleBtns.forEach(b => b.setAttribute('aria-expanded','false'));
    };
    const isOpen = () => !menu.classList.contains('pointer-events-none');

    toggleBtns.forEach(btn => on(btn, 'click', (e) => {
      e.stopPropagation();
      isOpen() ? close() : open();
    }));

    on(document, 'click', (e) => {
      if (isOpen() && !group.contains(e.target)) close();
    });
    on(document, 'keydown', (e) => { if (e.key === 'Escape' && isOpen()) close(); });
  })();

  // ---- Menús secundarios (Productos / Servicios)
  (function secondaryMenus() {
    const MENUS = ['productos','servicios'];

    function setMenuState(container, open) {
      const panel = container.querySelector('[role="menu"]');
      if (!panel) return;
      panel.classList.toggle('visible', open);
      panel.classList.toggle('pointer-events-auto', open);
      panel.classList.toggle('opacity-100', open);
      panel.classList.toggle('translate-y-0', open);
      panel.classList.toggle('scale-100', open);

      panel.classList.toggle('invisible', !open);
      panel.classList.toggle('pointer-events-none', !open);
      panel.classList.toggle('opacity-0', !open);
      panel.classList.toggle('translate-y-2', !open);
      panel.classList.toggle('scale-95', !open);

      const btn = container.querySelector('button');
      if (btn) btn.setAttribute('aria-expanded', open ? 'true' : 'false');
    }

    function closeAll(exceptId = null) {
      MENUS.forEach(id => {
        const c = document.querySelector(`[data-menu="${id}"]`);
        if (!c) return;
        if (exceptId && exceptId === id) return;
        setMenuState(c, false);
      });
    }

    MENUS.forEach(id => {
      const container = document.querySelector(`[data-menu="${id}"]`);
      if (!container) return;
      const btn = container.querySelector('button'); // el <a> contiene un botón en desktop; si no, ignora
      if (btn) {
        on(btn, 'click', (e) => {
          // en móvil: toggle por click
          const isOpen = container.querySelector('[role="menu"]').classList.contains('visible');
          closeAll(isOpen ? null : id);
          setMenuState(container, !isOpen);
          e.preventDefault();
          e.stopPropagation();
        });
      }
    });

    on(document, 'click', (e) => {
      const anyInside = e.target.closest('[data-menu="productos"],[data-menu="servicios"]');
      if (!anyInside) closeAll();
    });

    // Suavizar cierre con un pequeño delay al salir del hover
    $$('.group[data-menu]').forEach((g) => {
      let hideTO;
      on(g, 'mouseenter', () => {
        clearTimeout(hideTO);
        const panel = g.querySelector('[role="menu"]');
        if (panel) setMenuState(g, true);
      });
      on(g, 'mouseleave', () => {
        hideTO = setTimeout(() => setMenuState(g, false), 80);
      });
    });
  })();

  // ---- Buscador a la API (con render dinámico + “Agregar al carrito” por fetch)
  (function searchProducts() {
    const form = $('#buscador-api');
    const input = $('#query');
    const grid = $('#product-grid'); // debe existir en las vistas de catálogo/listado
    if (!form || !input || !grid || !API_BASE_URL) return;

    on(form, 'submit', async (e) => {
      e.preventDefault();
      const q = input.value.trim();
      if (!q) return;

      grid.innerHTML = '<p class="col-span-3 text-center text-gray-500">Buscando...</p>';

      try {
        const res = await fetch(`${API_BASE_URL}productos/?search=${encodeURIComponent(q)}`);
        const data = await res.json();

        grid.innerHTML = '';
        const results = data?.results || [];
        if (!results.length) {
          grid.innerHTML = '<p class="col-span-3 text-center text-red-600">No se encontraron resultados.</p>';
          return;
        }

        results.forEach(p => {
          const card = document.createElement('div');
          card.className = 'bg-[#F5E6CA] shadow-md rounded-lg overflow-hidden hover:shadow-lg transition-shadow duration-300';

          const imageSrc = p.imagen_url || (document.querySelector('link[rel="icon"]')?.href.replace('logo-pestana.png', 'images/no-image.jpg') || '/static/images/no-image.jpg');
          const precio = p.precio_actual ?? 0;

          card.innerHTML = `
            <img src="${imageSrc}" alt="${p.nombre}" class="w-full h-64 object-cover">
            <div class="p-5">
              <h3 class="text-lg font-semibold text-gray-900 mb-1">${p.nombre}</h3>
              <p class="text-sm text-gray-600 mb-2">${(p.descripcion || '').slice(0, 100)}</p>
              <p class="text-xl font-bold text-[#BD6A5C] mb-4">$${precio}</p>
              <div class="flex flex-col gap-2">
                <a href="/store/producto/${p.id}/" class="text-center bg-[#F5E6CA] border border-gray-800 text-gray-800 hover:bg-[#4B302D] hover:text-white font-medium py-2 px-4 rounded transition-colors">
                  Ver detalles
                </a>
                <button type="button" class="w-full bg-[#BD6A5C] hover:bg-[#D6B79E] text-white font-medium py-2 px-4 rounded transition-colors"
                        data-action="add-to-cart" data-product-id="${p.id}">
                  Agregar al carrito
                </button>
              </div>
            </div>
          `;
          grid.appendChild(card);
        });
      } catch (err) {
        grid.innerHTML = `<p class="col-span-3 text-center text-red-600">Error: ${err.message}</p>`;
      }
    });

    // CSRF helper (por si el endpoint requiere POST protegido)
    function getCookie(name) {
      const value = `; ${document.cookie}`;
      const parts = value.split(`; ${name}=`);
      if (parts.length === 2) return parts.pop().split(';').shift();
    }
    const csrftoken = getCookie('csrftoken');

    // Delegar add-to-cart
    delegate(document, 'click', '[data-action="add-to-cart"]', async (e, btn) => {
      const id = btn.dataset.productId;
      if (!id) return;
      try {
        const res = await fetch(`/cart/add/${id}/`, {
          method: 'POST',
          headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': csrftoken || '',
          },
        });
        if (!res.ok) throw new Error('No se pudo agregar al carrito.');
        // feedback simple
        btn.textContent = 'Agregado ✅';
        setTimeout(() => (btn.textContent = 'Agregar al carrito'), 1500);
      } catch (err) {
        alert(err.message);
      }
    });
  })();
})();
