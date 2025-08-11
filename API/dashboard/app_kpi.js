// KPI Management & Animations
(function(){
  window.App = window.App || {};
  
  // Проверка jQuery
  const $ = window.jQuery || window.$;
  if (!$) {
    console.error('jQuery не загружен! KPI модуль не может работать.');
    return;
  }

  const KPI = {
    // Инициализация KPI модуля
    init: function() {
      this.setupKPIAnimations();
      this.setupKPIInteractions();
      this.setupKPIUpdates();
      console.log('KPI модуль инициализирован');
    },

    // Настройка анимаций KPI
    setupKPIAnimations: function() {
      // Анимация появления при загрузке
      const kpiCards = $('.kpi');
      
      // Добавляем класс для анимации
      kpiCards.addClass('kpi-animate');
      
      // Анимация при скролле
      this.observeKPIVisibility();
      
      // Анимация при обновлении данных
      this.setupDataUpdateAnimations();
    },

    // Наблюдение за видимостью KPI для анимаций
    observeKPIVisibility: function() {
      if ('IntersectionObserver' in window) {
        const observer = new IntersectionObserver((entries) => {
          entries.forEach(entry => {
            if (entry.isIntersecting) {
              entry.target.classList.add('kpi-visible');
              observer.unobserve(entry.target);
            }
          });
        }, {
          threshold: 0.1,
          rootMargin: '50px'
        });

        $('.kpi').each(function() {
          observer.observe(this);
        });
      }
    },

    // Настройка анимаций обновления данных
    setupDataUpdateAnimations: function() {
      // Анимация при изменении значений
      this.setupValueChangeAnimation();
      
      // Анимация при обновлении статуса
      this.setupStatusUpdateAnimation();
    },

    // Анимация изменения значений
    setupValueChangeAnimation: function() {
      const kpiValues = $('.kpi-value');
      
      // Добавляем класс для анимации изменения
      kpiValues.addClass('kpi-value-animate');
      
      // Наблюдаем за изменениями в DOM
      const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
          if (mutation.type === 'childList' && mutation.target.classList.contains('kpi-value')) {
            this.animateValueChange(mutation.target);
          }
        });
      });

      kpiValues.each(function() {
        observer.observe(this, { childList: true });
      });
    },

    // Анимация изменения значения
    animateValueChange: function(element) {
      const $element = $(element);
      
      // Добавляем класс анимации
      $element.addClass('kpi-value-updating');
      
      // Убираем класс через время анимации
      setTimeout(() => {
        $element.removeClass('kpi-value-updating');
      }, 600);
    },

    // Настройка анимаций статуса
    setupStatusUpdateAnimation: function() {
      // Анимация для тренда баланса
      this.setupBalanceTrendAnimation();
      
      // Анимация для статуса обновления
      this.setupUpdateStatusAnimation();
      
      // Анимация для бейджа позиций
      this.setupPositionsBadgeAnimation();
    },

    // Анимация тренда баланса
    setupBalanceTrendAnimation: function() {
      const $trend = $('#kpi-balance-trend');
      
      if ($trend.length) {
        // Добавляем анимацию пульсации для положительного тренда
        $trend.on('classChange', function() {
          if ($(this).hasClass('positive')) {
            $(this).addClass('kpi-trend-pulse');
            setTimeout(() => {
              $(this).removeClass('kpi-trend-pulse');
            }, 1000);
          }
        });
      }
    },

    // Анимация статуса обновления
    setupUpdateStatusAnimation: function() {
      const $status = $('#kpi-updated-status');
      
      if ($status.length) {
        // Анимация при изменении статуса
        $status.on('classChange', function() {
          const $this = $(this);
          
          if ($this.hasClass('fresh')) {
            $this.addClass('kpi-status-fresh');
            setTimeout(() => {
              $this.removeClass('kpi-status-fresh');
            }, 800);
          } else if ($this.hasClass('stale')) {
            $this.addClass('kpi-status-stale');
            setTimeout(() => {
              $this.removeClass('kpi-status-stale');
            }, 800);
          }
        });
      }
    },

    // Анимация бейджа позиций
    setupPositionsBadgeAnimation: function() {
      const $badge = $('#kpi-positions-badge');
      
      if ($badge.length) {
        // Анимация при изменении количества позиций
        $badge.on('contentChange', function() {
          $(this).addClass('kpi-badge-update');
          setTimeout(() => {
            $(this).removeClass('kpi-badge-update');
          }, 600);
        });
      }
    },

    // Настройка интерактивности KPI
    setupKPIInteractions: function() {
      // Клик по KPI карточке
      $('.kpi').on('click', function(e) {
        if (e.target.closest('.kpi-icon') || e.target.closest('.kpi-value')) {
          KPI.handleKPIClick($(this));
        }
      });

      // Hover эффекты
      $('.kpi').on('mouseenter', function() {
        KPI.handleKPIHover($(this), true);
      }).on('mouseleave', function() {
        KPI.handleKPIHover($(this), false);
      });

      // Touch события для мобильных
      if ('ontouchstart' in window) {
        $('.kpi').on('touchstart', function() {
          KPI.handleKPITouch($(this));
        });
      }
    },

    // Обработка клика по KPI
    handleKPIClick: function($kpi) {
      const kpiType = $kpi.data('kpi-type');
      
      // Добавляем анимацию клика
      $kpi.addClass('kpi-clicked');
      
      // Убираем класс через время анимации и восстанавливаем pointer-events
      setTimeout(() => {
        $kpi.removeClass('kpi-clicked');
      }, 200);

      // Логируем действие
      console.log(`KPI клик: ${kpiType}`);
      
      // Здесь можно добавить специфичную логику для каждого типа KPI
      switch(kpiType) {
        case 'balance':
          this.showBalanceDetails();
          break;
        case 'positions':
          this.showPositionsDetails();
          break;
        case 'updated':
          this.showUpdateDetails();
          break;
        case 'file':
          this.showFileDetails();
          break;
      }
    },

    // Обработка hover эффектов
    handleKPIHover: function($kpi, isHovering) {
      // Не применяем hover эффекты во время анимации клика
      if ($kpi.hasClass('kpi-clicked')) {
        return;
      }
      
      if (isHovering) {
        $kpi.addClass('kpi-hovered');
      } else {
        $kpi.removeClass('kpi-hovered');
      }
    },

    // Обработка touch событий
    handleKPITouch: function($kpi) {
      // Не применяем touch анимацию во время анимации клика
      if ($kpi.hasClass('kpi-clicked')) {
        return;
      }
      
      $kpi.addClass('kpi-touched');
      setTimeout(() => {
        $kpi.removeClass('kpi-touched');
      }, 300);
    },

    // Показать детали баланса
    showBalanceDetails: function() {
      // Переход к вкладке "Баланс и позиции"
      const stateTab = $('#state-tab');
      if (stateTab.length) {
        stateTab.tab('show');
        console.log('Переход к вкладке "Баланс и позиции"');
      }
    },

    // Показать детали позиций
    showPositionsDetails: function() {
      // Переход к вкладке с позициями
      const positionsTab = $('#state-tab');
      if (positionsTab.length) {
        positionsTab.tab('show');
        console.log('Переход к вкладке "Баланс и позиции"');
      }
    },

    // Показать детали обновления
    showUpdateDetails: function() {
      // Переход к вкладке "График цен"
      const chartTab = $('#chart-tab');
      if (chartTab.length) {
        chartTab.tab('show');
        console.log('Переход к вкладке "График цен"');
      }
    },

    // Показать детали файла
    showFileDetails: function() {
      // Переход к вкладке с CSV данными
      const csvTab = $('#csv-tab');
      if (csvTab.length) {
        csvTab.tab('show');
        console.log('Переход к вкладке "CSV данные"');
      }
    },

    // Настройка обновлений KPI
    setupKPIUpdates: function() {
      // Автоматическое обновление каждые 30 секунд
      setInterval(() => {
        this.updateKPIStatuses();
      }, 30000);

      // Обновление при фокусе на странице
      $(window).on('focus', () => {
        this.updateKPIStatuses();
      });
    },

    // Обновление статусов KPI
    updateKPIStatuses: function() {
      // Обновление статуса последнего обновления
      this.updateLastUpdateStatus();
      
      // Обновление индикаторов файлов
      this.updateFileIndicators();
      
      // Обновление трендов баланса
      this.updateBalanceTrends();
    },

    // Обновление статуса последнего обновления
    updateLastUpdateStatus: function() {
      const $status = $('#kpi-updated-status');
      if ($status.length) {
        // Здесь можно добавить логику определения свежести данных
        const now = new Date();
        const lastUpdate = new Date(); // Здесь должно быть реальное время последнего обновления
        
        const diffMinutes = Math.floor((now - lastUpdate) / (1000 * 60));
        
        $status.removeClass('fresh stale').addClass(
          diffMinutes < 5 ? 'fresh' : 'stale'
        );
      }
    },

    // Обновление индикаторов файлов
    updateFileIndicators: function() {
      const $indicator = $('#kpi-file-indicator');
      if ($indicator.length) {
        // Здесь можно добавить логику проверки состояния файлов
        $indicator.addClass('kpi-indicator-active');
        setTimeout(() => {
          $indicator.removeClass('kpi-indicator-active');
        }, 500);
      }
    },

    // Обновление трендов баланса
    updateBalanceTrends: function() {
      const $trend = $('#kpi-balance-trend');
      if ($trend.length) {
        // Здесь можно добавить логику определения тренда
        // Пока просто переключаем классы для демонстрации
        const isPositive = Math.random() > 0.5;
        $trend.removeClass('positive negative').addClass(
          isPositive ? 'positive' : 'negative'
        );
      }
    },

    // Публичные методы для внешнего использования
    refreshKPI: function() {
      this.updateKPIStatuses();
      console.log('KPI обновлены');
    },

    animateKPI: function(kpiType) {
      const $kpi = $(`.kpi[data-kpi-type="${kpiType}"]`);
      if ($kpi.length) {
        $kpi.addClass('kpi-highlight');
        setTimeout(() => {
          $kpi.removeClass('kpi-highlight');
        }, 1000);
      }
    }
  };

  // Добавляем в глобальный App объект
  window.App.kpi = KPI;

  // Инициализация при готовности DOM
  $(document).ready(function() {
    KPI.init();
  });

  // Экспорт для использования в других модулях
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = KPI;
  }
})();
