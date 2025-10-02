// auto_adapt.js: динамическая адаптация элементов интерфейса под доступную ширину
(function() {
  const LEVELS = [
    { cls: 'auto-compact', width: 1250 },
    { cls: 'auto-compact-md', width: 1100 },
    { cls: 'auto-compact-sm', width: 960 },
    { cls: 'auto-compact-xs', width: 720 },
    { cls: 'auto-compact-xxs', width: 520 }
  ];

  function applyLevels(w) {
    const body = document.body;
    LEVELS.forEach(level => {
      if (w <= level.width) body.classList.add(level.cls); else body.classList.remove(level.cls);
    });
  }

  function adaptShortText() {
    document.querySelectorAll('[data-short-text]').forEach(el => {
      if (!el.dataset.originalText) el.dataset.originalText = el.textContent.trim();
      const orig = el.dataset.originalText;
      const limit = parseInt(el.dataset.shortLimit || '6', 10);
      const at = parseInt(el.dataset.shortAt || '960', 10);
      if (window.innerWidth <= at && orig.length > limit) {
        el.textContent = orig.slice(0, limit) + '…';
      } else {
        el.textContent = orig;
      }
    });
  }

  function hideBelow() {
    document.querySelectorAll('[data-hide-below]').forEach(el => {
      const th = parseInt(el.dataset.hideBelow, 10);
      if (window.innerWidth <= th) el.classList.add('d-none'); else el.classList.remove('d-none');
    });
  }

  // Универсальное переполнение функциональных элементов -> в меню "три точки"
  let overflowState = { items: [] };

  function clearEllipsisDynamic() {
    const menu = document.getElementById('compactExtraMenu');
    const wrapper = document.querySelector('.compact-ellipsis-wrapper');
    if (!menu) return;
    Array.from(menu.querySelectorAll('li[data-overflow-clone]')).forEach(li => li.remove());
    overflowState.items.forEach(entry => {
      if (entry.placeholder && entry.original) {
        entry.original.classList.remove('d-none');
        if (entry.placeholder.parentNode) {
          entry.placeholder.parentNode.insertBefore(entry.original, entry.placeholder);
          entry.placeholder.remove();
        }
      }
    });
    overflowState.items = [];
    if (wrapper) wrapper.classList.remove('ellipsis-visible');
  }

  function relocateOverflow() {
    const container = document.querySelector('.nav-functional');
    const list = document.getElementById('primaryNavItems');
    const menu = document.getElementById('compactExtraMenu');
    if (!container || !list || !menu) return;

    // Сначала очистить прошлое состояние
    clearEllipsisDynamic();

    const availableWidth = container.clientWidth - 16; // небольшой запас
    // Собираем функциональные элементы
    const functionalItems = Array.from(list.querySelectorAll('li[data-functional-item]'));
    if (!functionalItems.length) return;

    // Подсчитываем ширину если все видимы
    let widthAccum = 0;
    functionalItems.forEach(li => {
      li.classList.remove('d-none');
      widthAccum += li.offsetWidth;
    });

    // Если влезают все — выход
    if (widthAccum <= availableWidth) {
      // убедимся что меню скрыто
      const wrapper = document.querySelector('.compact-ellipsis-wrapper');
      if (wrapper) wrapper.classList.remove('ellipsis-visible');
      return;
    }

    // Сортировка по приоритету (большее значение переносим раньше)
    const sorted = functionalItems.sort((a,b) => {
      const pa = parseInt(a.dataset.functionalPriority || '50',10);
      const pb = parseInt(b.dataset.functionalPriority || '50',10);
      return pb - pa;
    });

    // Переносим пока не влезет
    sorted.forEach(li => {
      if (widthAccum <= availableWidth) return;
      const ph = document.createElement('li');
      ph.style.display = 'none';
      ph.className = 'functional-placeholder';
      li.parentNode.insertBefore(ph, li);
      const anchor = li.querySelector('a.nav-link');
      if (anchor) {
        const cloneLi = document.createElement('li');
        cloneLi.setAttribute('data-overflow-clone','1');
        cloneLi.innerHTML = '<a class="dropdown-item" href="' + anchor.getAttribute('href') + '">' + anchor.textContent.trim() + '</a>';
        menu.appendChild(cloneLi);
      }
      li.classList.add('d-none');
      overflowState.items.push({ placeholder: ph, original: li });
      widthAccum -= li.offsetWidth;
    });
    if (overflowState.items.length) {
      const wrapper = document.querySelector('.compact-ellipsis-wrapper');
      if (wrapper) wrapper.classList.add('ellipsis-visible');
    }
  }

  // === ИНТЕЛЛЕКТУАЛЬНАЯ АДАПТАЦИЯ ВСЕХ УСТРОЙСТВ ===
  function adaptForAllDevices() {
    const viewport = window.innerWidth;
    
    // Определить категорию устройства
    let deviceCategory = 'mobile-small';
    if (viewport >= 1400) deviceCategory = 'desktop-xl';
    else if (viewport >= 1200) deviceCategory = 'desktop-large'; 
    else if (viewport >= 992) deviceCategory = 'desktop-medium';
    else if (viewport >= 768) deviceCategory = 'tablet';
    else if (viewport >= 576) deviceCategory = 'mobile-large';
    
    console.log(`Адаптация для устройства: ${deviceCategory} (${viewport}px)`);
    
    // Применить классы для категории устройства
    document.body.className = document.body.className.replace(/device-\w+/g, '');
    document.body.classList.add(`device-${deviceCategory}`);
    
    // Интеллектуальная адаптация элементов
    adaptNavbarElements(deviceCategory, viewport);
    adaptGuestBadge(deviceCategory, viewport);
    adaptProfileBlock(deviceCategory, viewport);
    adaptEllipsisButton(deviceCategory, viewport);
  }
  
  // Адаптация элементов навбара
  function adaptNavbarElements(category, viewport) {
    const navbar = document.querySelector('.navbar-modern');
    if (!navbar) return;
    
    // Динамические размеры в зависимости от устройства
    const sizingConfig = {
      'desktop-xl': { linkPadding: '8px 16px', fontSize: '1rem', brandSize: '1.1rem' },
      'desktop-large': { linkPadding: '7px 14px', fontSize: '0.95rem', brandSize: '1.05rem' },
      'desktop-medium': { linkPadding: '6px 12px', fontSize: '0.9rem', brandSize: '1rem' },
      'tablet': { linkPadding: '5px 10px', fontSize: '0.85rem', brandSize: '0.95rem' },
      'mobile-large': { linkPadding: '4px 8px', fontSize: '0.8rem', brandSize: '0.9rem' },
      'mobile-small': { linkPadding: '3px 6px', fontSize: '0.75rem', brandSize: '0.85rem' }
    };
    
    const config = sizingConfig[category];
    if (config) {
      // Адаптация ссылок навигации
      navbar.querySelectorAll('.nav-link').forEach(link => {
        link.style.setProperty('padding', config.linkPadding, 'important');
        link.style.fontSize = config.fontSize;
      });
      
      // Адаптация бренда
      const brand = navbar.querySelector('.navbar-brand');
      if (brand) {
        brand.style.fontSize = config.brandSize;
      }
      
      // Скрытие текста бренда на мобильных
      const brandText = navbar.querySelector('.brand-text');
      if (brandText) {
        brandText.style.display = (category.includes('mobile')) ? 'none' : 'inline';
      }
    }
  }
  
  // Адаптация гостевого бейджа
  function adaptGuestBadge(category, viewport) {
    const badge = document.querySelector('.guest-badge-fixed .badge');
    if (!badge) return;
    
    const badgeConfig = {
      'desktop-xl': { padding: '0.5rem 1rem', fontSize: '0.875rem' },
      'desktop-large': { padding: '0.45rem 0.9rem', fontSize: '0.8rem' },
      'desktop-medium': { padding: '0.4rem 0.8rem', fontSize: '0.75rem' },
      'tablet': { padding: '0.35rem 0.7rem', fontSize: '0.7rem' },
      'mobile-large': { padding: '0.3rem 0.6rem', fontSize: '0.65rem' },
      'mobile-small': { padding: '0.25rem 0.5rem', fontSize: '0.6rem' }
    };
    
    const config = badgeConfig[category];
    if (config) {
      badge.style.setProperty('padding', config.padding, 'important');
      badge.style.setProperty('fontSize', config.fontSize, 'important');
    }
  }
  
  // Адаптация блока профиля
  function adaptProfileBlock(category, viewport) {
    const userName = document.querySelector('.nav-profile .user-name');
    const avatar = document.querySelector('.avatar-thumb');
    
    // Скрытие имени пользователя на малых экранах
    if (userName) {
      const shouldHide = (category === 'tablet' || category.includes('mobile'));
      userName.style.setProperty('display', shouldHide ? 'none' : 'inline', 'important');
    }
    
    // Адаптация размера аватара
    if (avatar) {
      const avatarSizes = {
        'mobile-small': '26px',
        'mobile-large': '28px'
      };
      
      if (avatarSizes[category]) {
        avatar.style.width = avatarSizes[category];
        avatar.style.height = avatarSizes[category];
      }
    }
  }
  
  // Адаптация кнопки ellipsis
  function adaptEllipsisButton(category, viewport) {
    const ellipsisBtn = document.querySelector('.nav-ellipsis-btn');
    if (!ellipsisBtn) return;
    
    if (category === 'mobile-small') {
      ellipsisBtn.style.padding = '3px 8px';
      ellipsisBtn.style.fontSize = '0.8rem';
    }
  }

  let raf = null;
  function onResize() {
    if (raf) cancelAnimationFrame(raf);
    raf = requestAnimationFrame(() => {
      const w = window.innerWidth;
      
      // Полная адаптация для всех устройств
      adaptForAllDevices();
      
      // Стандартные функции адаптации
      applyLevels(w);
      adaptShortText();
      hideBelow();
      relocateOverflow();
    });
  }

  window.addEventListener('resize', onResize);
  window.addEventListener('DOMContentLoaded', onResize);
})();
