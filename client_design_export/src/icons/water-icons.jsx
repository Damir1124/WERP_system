/**
 * water-icons.jsx
 * -----------------------------------------------------------------------
 * Набор SVG-иконок с водной тематикой для замены emoji в мини-приложении.
 * Чистые React-компоненты, без внешних зависимостей (лёгкие, inline SVG).
 *
 * Как использовать:
 *   import { ICONS, TYPE_ICONS, STATUS_ICONS, PAYMENT_ICONS, FLAG_ICONS } from './water-icons';
 *
 *   <ICONS.cart size={24} />
 *   <TYPE_ICONS.WE size={20} color="#0EA5E9" />
 *   <STATUS_ICONS.pending size={16} />
 *
 * Каждый компонент принимает пропсы:
 *   size?: number  (по умолчанию 24)
 *   color?: string (по умолчанию 'currentColor' — наследует цвет текста)
 *   className?: string
 *   strokeWidth?: number (по умолчанию 1.8)
 *
 * Палитра (если нужно явно красить, а не наследовать currentColor):
 *   --water-500: #0EA5E9  (основной)
 *   --water-600: #0284C7  (акцент/иконки действий)
 *   --water-300: #7DD3FC  (light/disabled)
 *   --water-900: #0C4A6E  (тёмный, текст на иконках)
 *   --water-teal: #06B6D4 (вторичный акцент)
 * -----------------------------------------------------------------------
 */

import React from 'react';

const Base = ({ size = 24, color = 'currentColor', strokeWidth = 1.8, className = '', children, viewBox = '0 0 24 24' }) => (
  <svg
    width={size}
    height={size}
    viewBox={viewBox}
    fill="none"
    stroke={color}
    strokeWidth={strokeWidth}
    strokeLinecap="round"
    strokeLinejoin="round"
    className={className}
    aria-hidden="true"
  >
    {children}
  </svg>
);

/* =======================================================================
   1. НАВИГАЦИЯ И ИНТЕРФЕЙС
   ======================================================================= */

// 🛒 Корзина — App.jsx (нижняя навигация), Catalog.jsx, Cart.jsx (плавающая кнопка, пустая корзина)
// Тележка с каплей воды вместо одного из товаров — фирменный акцент
export const IconCart = (props) => (
  <Base {...props}>
    <path d="M3 4h2l1.6 9.6a2 2 0 0 0 2 1.7h7.1a2 2 0 0 0 2-1.6L19 8H6" />
    <circle cx="9.5" cy="19.5" r="1.4" fill={props.color || 'currentColor'} stroke="none" />
    <circle cx="16" cy="19.5" r="1.4" fill={props.color || 'currentColor'} stroke="none" />
    <path d="M12.2 9.2c0 1.2-.9 1.9-1.9 1.9-1.1 0-1.9-.7-1.9-1.9 0-1.1 1.9-3 1.9-3s1.9 1.9 1.9 3z" fill={props.color || 'currentColor'} stroke="none" opacity="0.9" />
  </Base>
);

// 📦 Заказы — App.jsx (вкладка навигации), MyOrders.jsx (индикатор загрузки)
export const IconOrders = (props) => (
  <Base {...props}>
    <path d="M3.5 8.5 12 4l8.5 4.5V16L12 20.5 3.5 16z" />
    <path d="M3.5 8.5 12 13l8.5-4.5" />
    <path d="M12 13v7.5" />
  </Base>
);

// 📍 Адреса/геолокация — App.jsx, Cart.jsx, OrderForm.jsx, MyAddresses.jsx, LocationPicker.jsx
// Маркер выполнен в форме капли
export const IconLocation = (props) => (
  <Base {...props}>
    <path d="M12 21.5c4.2-4.8 7-8.3 7-11.8A7 7 0 0 0 5 9.7c0 3.5 2.8 7 7 11.8z" />
    <circle cx="12" cy="9.7" r="2.4" />
  </Base>
);

// 🌐 Выбор языка — App.jsx, i18n.js
// Глобус с волнистыми "меридианами" — намёк на воду
export const IconLanguage = (props) => (
  <Base {...props}>
    <circle cx="12" cy="12" r="8.5" />
    <path d="M3.5 10.5c2 1.4 4 1.4 8.5 1.4s6.5 0 8.5-1.4" />
    <path d="M3.5 14.5c2-1.4 4-1.4 8.5-1.4s6.5 0 8.5 1.4" />
    <path d="M12 3.5c2.3 2.4 3.4 5.3 3.4 8.5s-1.1 6.1-3.4 8.5c-2.3-2.4-3.4-5.3-3.4-8.5s1.1-6.1 3.4-8.5z" />
  </Base>
);

// ⚠️ Предупреждение «Откройте в Telegram» — App.jsx
export const IconWarning = (props) => (
  <Base {...props}>
    <path d="M12 3.5 21.5 20h-19z" />
    <path d="M12 9.5v4.2" />
    <circle cx="12" cy="17" r="0.15" fill={props.color || 'currentColor'} stroke={props.color || 'currentColor'} strokeWidth="1.6" />
  </Base>
);

// ❌ Ошибка подключения / статус «Отменён» — App.jsx, MyOrders.jsx
export const IconError = (props) => (
  <Base {...props}>
    <circle cx="12" cy="12" r="8.5" />
    <path d="M9 9l6 6M15 9l-6 6" />
  </Base>
);

// ✕ Кнопка закрытия карты — LocationPicker.jsx
export const IconClose = (props) => (
  <Base {...props}>
    <path d="M6 6l12 12M18 6L6 18" />
  </Base>
);

/* =======================================================================
   2. БРЕНД И ТОВАРЫ
   ======================================================================= */

// 💧 Логотип / загрузка / fallback-изображение товара / тип товара «Вода» (WE)
// Основной фирменный знак — капля с бликом
export const IconWaterDrop = (props) => (
  <Base {...props}>
    <path d="M12 2.5c3.6 4.6 7 8.9 7 12.8a7 7 0 1 1-14 0c0-3.9 3.4-8.2 7-12.8z" />
    <path d="M9.3 15.5a2.7 2.7 0 0 0 2.4 2.5" opacity="0.7" />
  </Base>
);

// 🪣 Тип товара «Баклажка 20л» (B20L) — Catalog.jsx, OrderForm.jsx
export const IconBottle20L = (props) => (
  <Base {...props}>
    <path d="M9 3h6v2.6l1.6 2A2 2 0 0 1 17 9v9.5A2.5 2.5 0 0 1 14.5 21h-5A2.5 2.5 0 0 1 7 18.5V9a2 2 0 0 1 .4-1.4L9 5.6z" />
    <path d="M9 3h6" />
    <path d="M8.6 12.5h6.8" opacity="0.6" />
    <path d="M11.4 15.3c0 .6-.5 1-1 1s-1-.4-1-1 1-1.6 1-1.6 1 1 1 1.6z" fill={props.color || 'currentColor'} stroke="none" opacity="0.85" />
  </Base>
);

// 🫙 Тип товара «Бутылка» (BT) — Catalog.jsx
export const IconBottle = (props) => (
  <Base {...props}>
    <path d="M10.2 2.5h3.6v2.8l1 1.3a2 2 0 0 1 .4 1.2v10.7A2.5 2.5 0 0 1 12.7 21h-1.4A2.5 2.5 0 0 1 8.8 18.5V7.8a2 2 0 0 1 .4-1.2l1-1.3z" />
    <path d="M10.2 2.5h3.6" />
    <path d="M8.9 11.8h6.2" opacity="0.6" />
  </Base>
);

// 🧊 Тип товара «Кулер/лёд» (CL) — Catalog.jsx
export const IconCooler = (props) => (
  <Base {...props}>
    <rect x="4" y="9" width="16" height="11" rx="1.6" />
    <path d="M4 13h16" />
    <path d="M8 9V6.5A2.5 2.5 0 0 1 10.5 4h3A2.5 2.5 0 0 1 16 6.5V9" />
    <path d="M9 16.2h2.4M14.6 16.2H17" opacity="0.7" />
  </Base>
);

// 🔧 Тип товара «Аксессуары» (AR) — Catalog.jsx
export const IconAccessories = (props) => (
  <Base {...props}>
    <path d="M16.6 4.4a4 4 0 0 0-5.4 4.6L4 16.2v3.4h3.4L14.6 12.8a4 4 0 0 0 4.6-5.4l-2.7 2.7-2-2z" />
  </Base>
);

// 📭 Пустой список (нет товаров/заказов/адресов) — Catalog.jsx, MyOrders.jsx, MyAddresses.jsx
export const IconEmpty = (props) => (
  <Base {...props}>
    <path d="M3.5 9.5 8 4h8l4.5 5.5" />
    <path d="M3.5 9.5h5.2c.3 1.6 1.5 2.5 3.3 2.5s3-.9 3.3-2.5h5.2V18a1.7 1.7 0 0 1-1.7 1.7H5.2A1.7 1.7 0 0 1 3.5 18z" />
    <path d="M9.5 8.5h5" opacity="0.6" />
  </Base>
);

/* =======================================================================
   3. СТАТУСЫ ЗАКАЗОВ
   ======================================================================= */

// ⏳ Статус «Ожидает» + поиск геолокации — MyOrders.jsx, i18n.js, LocationPicker.jsx
export const IconPending = (props) => (
  <Base {...props}>
    <circle cx="12" cy="12" r="8.5" />
    <path d="M12 7.5V12l3 2" />
  </Base>
);

// ✅ Статус «Доставлен» / подтверждение — MyOrders.jsx, i18n.js
export const IconDelivered = (props) => (
  <Base {...props}>
    <circle cx="12" cy="12" r="8.5" />
    <path d="M8.2 12.3l2.6 2.6 5-5.4" />
  </Base>
);

// ✏️ Кнопка «Редактировать» / загрузка редактора — MyOrders.jsx, OrderEdit.jsx
export const IconEdit = (props) => (
  <Base {...props}>
    <path d="M4 20l.9-3.6L16 5.3a1.8 1.8 0 0 1 2.6 0l0 0a1.8 1.8 0 0 1 0 2.6L7.5 19 4 20z" />
    <path d="M14.3 7l2.6 2.6" />
  </Base>
);

// 🗑 / 🗑️ Удаление товара/заказа/адреса — Cart.jsx, MyOrders.jsx, i18n.js
export const IconDelete = (props) => (
  <Base {...props}>
    <path d="M5 7h14" />
    <path d="M9 7V5.2A1.2 1.2 0 0 1 10.2 4h3.6A1.2 1.2 0 0 1 15 5.2V7" />
    <path d="M7 7l.8 12a2 2 0 0 0 2 1.9h4.4a2 2 0 0 0 2-1.9L17 7" />
    <path d="M10.2 11v6M13.8 11v6" opacity="0.6" />
  </Base>
);

/* =======================================================================
   4. ОПЛАТА И ДЕЙСТВИЯ
   ======================================================================= */

// 💵 Оплата наличными — i18n.js
export const IconCash = (props) => (
  <Base {...props}>
    <rect x="2.5" y="6.5" width="19" height="11" rx="1.6" />
    <circle cx="12" cy="12" r="2.8" />
    <path d="M5.5 9v0M18.5 15v0" />
  </Base>
);

// 💳 Оплата картой — i18n.js
export const IconCard = (props) => (
  <Base {...props}>
    <rect x="2.5" y="5.5" width="19" height="13" rx="2" />
    <path d="M2.5 10h19" />
    <path d="M6 14.5h4" opacity="0.7" />
  </Base>
);

// ➕ Добавить новый адрес — i18n.js
export const IconAdd = (props) => (
  <Base {...props}>
    <circle cx="12" cy="12" r="8.5" />
    <path d="M12 8v8M8 12h8" />
  </Base>
);

// 🔄 Кнопка «Обновить» — i18n.js
// Круговая стрелка выполнена как "водоворот"
export const IconRefresh = (props) => (
  <Base {...props}>
    <path d="M4.5 12a7.5 7.5 0 0 1 12.6-5.5L19.5 8" />
    <path d="M19.5 4v4h-4" />
    <path d="M19.5 12a7.5 7.5 0 0 1-12.6 5.5L4.5 16" />
    <path d="M4.5 20v-4h4" />
  </Base>
);

// 💾 Сохранить адрес / изменения — i18n.js
// Дискета с каплей вместо этикетки — фирменный акцент
export const IconSave = (props) => (
  <Base {...props}>
    <path d="M5 3.5h11.5L20.5 7.5V19a1.5 1.5 0 0 1-1.5 1.5H5A1.5 1.5 0 0 1 3.5 19V5A1.5 1.5 0 0 1 5 3.5z" />
    <path d="M7.5 3.5V9h8V3.5" />
    <path d="M12 12.2c1 1.1 1.7 2 1.7 2.8a1.7 1.7 0 1 1-3.4 0c0-.8.7-1.7 1.7-2.8z" fill={props.color || 'currentColor'} stroke="none" opacity="0.85" />
  </Base>
);

// 📋 Заголовок блока оформления заказа — Cart.jsx
export const IconChecklist = (props) => (
  <Base {...props}>
    <rect x="5" y="3.5" width="14" height="17" rx="1.6" />
    <path d="M9 3.5V2.8a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v.7" />
    <path d="M8 10.5l1.4 1.4L12 9M8 15.5l1.4 1.4L12 14" />
    <path d="M14.5 10.5h2.5M14.5 15.5h2.5" />
  </Base>
);

// 📡 Кнопка «Моя локация» — LocationPicker.jsx
export const IconMyLocation = (props) => (
  <Base {...props}>
    <circle cx="12" cy="12" r="2.4" />
    <path d="M12 3v2.6M12 18.4V21M3 12h2.6M18.4 12H21" />
    <path d="M12 5.6a6.4 6.4 0 1 1 0 12.8" opacity="0.6" />
  </Base>
);

// ✓ Кнопка «Подтвердить» на карте — LocationPicker.jsx
export const IconConfirm = (props) => (
  <Base {...props}>
    <path d="M5 12.5l4.5 4.5L19 7" />
  </Base>
);

// 🚚 Бесплатная доставка (приветствие) — i18n.js
// Капля на кузове — вода в доставке
export const IconDelivery = (props) => (
  <Base {...props}>
    <path d="M2.5 8h10.5v9h-10.5z" />
    <path d="M13 11h3.3l3.2 3v3h-1.5" />
    <circle cx="7" cy="18.7" r="1.6" />
    <circle cx="16.5" cy="18.7" r="1.6" />
    <path d="M16.7 13.5c0 .7-.6 1.3-1.3 1.3s-1.3-.6-1.3-1.3 1.3-2.2 1.3-2.2 1.3 1.5 1.3 2.2z" fill={props.color || 'currentColor'} stroke="none" opacity="0.85" />
  </Base>
);

/* =======================================================================
   5. ФЛАГИ ЯЗЫКОВ
   (упрощённые геометрические флаги, без деталей гербов — легко узнаваемые)
   ======================================================================= */

const FlagBase = ({ size = 24, className = '', children }) => (
  <svg width={size} height={size * 0.7} viewBox="0 0 28 20" className={className} aria-hidden="true">
    <rect x="0.5" y="0.5" width="27" height="19" rx="2.5" fill="#fff" stroke="#E2E8F0" />
    {children}
  </svg>
);

// 🇷🇺 Русский язык — i18n.js
export const FlagRU = (props) => (
  <FlagBase {...props}>
    <clipPath id="clip-ru"><rect x="0.5" y="0.5" width="27" height="19" rx="2.5" /></clipPath>
    <g clipPath="url(#clip-ru)">
      <rect x="0" y="0" width="28" height="6.7" fill="#FFFFFF" />
      <rect x="0" y="6.7" width="28" height="6.6" fill="#0039A6" />
      <rect x="0" y="13.3" width="28" height="6.7" fill="#D52B1E" />
    </g>
  </FlagBase>
);

// 🇺🇿 Узбекский язык — i18n.js
export const FlagUZ = (props) => (
  <FlagBase {...props}>
    <clipPath id="clip-uz"><rect x="0.5" y="0.5" width="27" height="19" rx="2.5" /></clipPath>
    <g clipPath="url(#clip-uz)">
      <rect x="0" y="0" width="28" height="6.2" fill="#1EB53A" />
      <rect x="0" y="6.2" width="28" height="0.7" fill="#fff" />
      <rect x="0" y="6.9" width="28" height="6.2" fill="#0099B5" />
      <rect x="0" y="13.1" width="28" height="0.7" fill="#fff" />
      <rect x="0" y="13.8" width="28" height="6.2" fill="#CE1126" />
      <circle cx="5" cy="4" r="2" fill="#fff" />
      <circle cx="5.8" cy="3.6" r="2" fill="#0099B5" />
    </g>
  </FlagBase>
);

// 🇬🇧 Английский язык — i18n.js
export const FlagGB = (props) => (
  <FlagBase {...props}>
    <clipPath id="clip-gb"><rect x="0.5" y="0.5" width="27" height="19" rx="2.5" /></clipPath>
    <g clipPath="url(#clip-gb)">
      <rect x="0" y="0" width="28" height="20" fill="#00247D" />
      <path d="M0 0l28 20M28 0L0 20" stroke="#fff" strokeWidth="3" />
      <path d="M0 0l28 20M28 0L0 20" stroke="#CF142B" strokeWidth="1.2" />
      <path d="M14 0v20M0 10h28" stroke="#fff" strokeWidth="5" />
      <path d="M14 0v20M0 10h28" stroke="#CF142B" strokeWidth="2.2" />
    </g>
  </FlagBase>
);

/* =======================================================================
   РЕЕСТРЫ — для быстрой замены по существующим маппингам в коде
   ======================================================================= */

// Полный список всех иконок по смысловому ключу
export const ICONS = {
  cart: IconCart,
  orders: IconOrders,
  location: IconLocation,
  language: IconLanguage,
  warning: IconWarning,
  error: IconError,
  close: IconClose,
  logo: IconWaterDrop,
  empty: IconEmpty,
  edit: IconEdit,
  delete: IconDelete,
  add: IconAdd,
  refresh: IconRefresh,
  save: IconSave,
  checklist: IconChecklist,
  myLocation: IconMyLocation,
  confirm: IconConfirm,
  delivery: IconDelivery,
};

// Замена TYPE_ICONS в Catalog.jsx (маппинг по коду типа товара)
// Коды соответствуют Product.TypeProduct в apps/products/models.py:
//   19W  — Вода
//   B19W — Вода + тара 19 (баклажка 20л)
//   BT   — Тара (бутылка)
//   CL   — Кулеры
//   AR   — Аксессуары
export const TYPE_ICONS = {
  '19W': IconWaterDrop,     // Вода
  'B19W': IconBottle20L,    // Вода + тара 19 (баклажка)
  'BT': IconBottle,         // Тара (бутылка)
  'CL': IconCooler,         // Кулеры
  'AR': IconAccessories,    // Аксессуары
};

// Замена статусных иконок в MyOrders.jsx / i18n.js
export const STATUS_ICONS = {
  pending: IconPending,
  delivered: IconDelivered,
  cancelled: IconError,
};

// Замена иконок оплаты в i18n.js
export const PAYMENT_ICONS = {
  cash: IconCash,
  card: IconCard,
};

// Замена флагов в i18n.js (выбор языка)
export const FLAG_ICONS = {
  ru: FlagRU,
  uz: FlagUZ,
  en: FlagGB,
};