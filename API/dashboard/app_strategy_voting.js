// Strategy Voting Animation Module
(function(){
  window.App = window.App || {};
  
  // Проверка jQuery
  const $ = window.jQuery || window.$;
  if (!$) {
    console.error('jQuery не загружен! Strategy Voting модуль не может работать.');
    return;
  }

  const StrategyVoting = {
    // Конфигурация стратегий и их весов
    strategyConfig: {
      "RSI": { weight: 0.20, color: "#6366f1" },
      "XGB": { weight: 0.30, color: "#8b5cf6" },
      "MACD": { weight: 0.20, color: "#06b6d4" },
      "BOLLINGER": { weight: 0.12, color: "#10b981" },
      "STOCHASTIC": { weight: 0.10, color: "#f59e0b" },
      "WILLIAMS_R": { weight: 0.08, color: "#ef4444" }
    },

    // Инициализация модуля
    init: function() {
      this.container = $('#strategy-voting');
      if (this.container.length === 0) {
        console.warn('Контейнер для анимации голосования не найден');
        return;
      }

      this.setupAnimation();
      this.setupDataMonitoring();
      console.log('Strategy Voting модуль инициализирован');
    },

    // Настройка анимации
    setupAnimation: function() {
      this.renderInitialBars();
      this.setupHoverEffects();
    },

    // Рендер начальных полос
    renderInitialBars: function() {
      this.container.empty();
      
      Object.keys(this.strategyConfig).forEach((strategyName, index) => {
        const bar = this.createStrategyBar(strategyName, 'hold', 0);
        this.container.append(bar);
      });
    },

    // Создание полосы стратегии
    createStrategyBar: function(strategyName, signal, weight) {
      const config = this.strategyConfig[strategyName];
      const bar = $('<div>', {
        class: `strategy-bar ${signal}`,
        'data-strategy': strategyName,
        'data-weight': weight,
        'data-signal': signal,
        'data-tooltip': `${strategyName}: ${signal.toUpperCase()}`
      });

      // Устанавливаем высоту на основе веса с увеличенной максимальной высотой
      if (signal === 'hold') {
        bar.css({
          'width': '6px',
          'height': '6px',
          'border-radius': '50%'
        });
      } else {
        // Увеличиваем максимальную высоту до 100px
        const height = Math.max(20, Math.min(100, weight * 120)); // Максимальная высота 100px
        bar.css({
          'height': `${height}px`,
          'min-height': '20px',
          'max-height': '100px'
        });
      }

      return bar;
    },

    // Настройка hover эффектов
    setupHoverEffects: function() {
      // Убираем стандартные подсказки браузера
      this.container.on('mouseenter', '.strategy-bar', function() {
        const $bar = $(this);
        // Убираем стандартный title для предотвращения появления браузерных подсказок
        $bar.removeAttr('title');
      });
    },

    // Настройка мониторинга данных
    setupDataMonitoring: function() {
      // Используем debouncing для обновлений
      const debouncedUpdate = window.App.util && window.App.util.debounce ? 
        window.App.util.debounce(() => {
          this.updateVotingAnimation();
        }, 2000) : 
        () => this.updateVotingAnimation();
      
      // Обновляем анимацию каждые 5 секунд
      this._updateTimer = setInterval(() => {
        debouncedUpdate();
      }, 5000);

      // Обновляем при изменении CSV данных
      this.monitorCSVChanges();
    },

    // Мониторинг изменений в CSV
    monitorCSVChanges: function() {
      // Слушаем события обновления данных
      $(document).on('csvDataUpdated', () => {
        this.updateVotingAnimation();
      });

      // Слушаем события обновления KPI
      $(document).on('kpiDataUpdated', () => {
        this.updateVotingAnimation();
      });
    },

    // Обновление анимации голосования
    updateVotingAnimation: function() {
      // Убираем вызов прогресс-бара для анимации голосования
      // чтобы не показывать полоску обновления сверху
      this.fetchStrategySignals().then((signals) => {
        this.updateBars(signals);
      }).catch((error) => {
        console.error('Ошибка при обновлении анимации голосования:', error);
      });
    },

    // Получение сигналов стратегий
    fetchStrategySignals: async function() {
      try {
        // Получаем последние данные из CSV без показа прогресс-бара
        // чтобы анимация голосования не вызывала полоску обновления сверху
        const response = await fetch('/api/candles?file=BTCUSDT_1m_anal.csv&tail=1', {
          cache: 'no-store' // Отключаем кэширование для получения свежих данных
        });
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        if (!data || data.length === 0) {
          return this.getDefaultSignals();
        }

        // Берем последнюю строку
        const lastRow = data[data.length - 1];
        return this.parseStrategySignals(lastRow);

      } catch (error) {
        console.warn('Не удалось получить данные стратегий, используем демо данные:', error);
        return this.getDemoSignals();
      }
    },

    // Парсинг сигналов стратегий из CSV строки
    parseStrategySignals: function(row) {
      const signals = {};
      
      // Маппинг колонок CSV на названия стратегий
      const columnMapping = {
        'orders_rsi': 'RSI',
        'orders_xgb': 'XGB',
        'orders_macd': 'MACD',
        'orders_bollinger': 'BOLLINGER',
        'orders_stochastic': 'STOCHASTIC',
        'orders_williams_r': 'WILLIAMS_R'
      };

      Object.entries(columnMapping).forEach(([column, strategy]) => {
        if (row[column] !== undefined && row[column] !== null) {
          const value = parseFloat(row[column]);
          if (!isNaN(value)) {
            signals[strategy] = {
              signal: this.normalizeSignal(value),
              weight: this.strategyConfig[strategy].weight,
              rawValue: value
            };
          }
        }
      });

      return signals;
    },

    // Нормализация сигнала
    normalizeSignal: function(value) {
      if (value > 0.1) return 'buy';
      if (value < -0.1) return 'sell';
      return 'hold';
    },

    // Получение сигналов по умолчанию
    getDefaultSignals: function() {
      const signals = {};
      Object.keys(this.strategyConfig).forEach(strategy => {
        signals[strategy] = {
          signal: 'hold',
          weight: this.strategyConfig[strategy].weight,
          rawValue: 0
        };
      });
      return signals;
    },

    // Получение демонстрационных сигналов для тестирования
    getDemoSignals: function() {
      // Генерируем случайные сигналы для демонстрации
      const signals = {};
      const strategies = Object.keys(this.strategyConfig);
      
      strategies.forEach(strategy => {
        const random = Math.random();
        let signal, rawValue;
        
        if (random < 0.3) {
          signal = 'buy';
          rawValue = 0.5 + Math.random() * 0.5; // 0.5 - 1.0
        } else if (random < 0.6) {
          signal = 'sell';
          rawValue = -0.5 - Math.random() * 0.5; // -0.5 - -1.0
        } else {
          signal = 'hold';
          rawValue = (Math.random() - 0.5) * 0.2; // -0.1 - 0.1
        }
        
        signals[strategy] = {
          signal: signal,
          weight: this.strategyConfig[strategy].weight,
          rawValue: rawValue
        };
      });
      
      return signals;
    },

    // Обновление полос
    updateBars: function(signals) {
      this.container.find('.strategy-bar').each((index, element) => {
        const $bar = $(element);
        const strategy = $bar.data('strategy');
        const signalData = signals[strategy];
        
        if (signalData) {
          this.updateBar($bar, signalData);
        }
      });
    },

    // Обновление отдельной полосы
    updateBar: function($bar, signalData) {
      const oldSignal = $bar.data('signal');
      const newSignal = signalData.signal;
      const weight = signalData.weight;

      // Если сигнал изменился, обновляем
      if (oldSignal !== newSignal || $bar.data('weight') !== weight) {
        // Добавляем класс для анимации обновления
        $bar.addClass('updating');
        
        // Обновляем данные
        $bar.data('signal', newSignal);
        $bar.data('weight', weight);
        
        // Обновляем классы и стили
        $bar.removeClass('buy sell hold').addClass(newSignal);
        // Обновляем подсказку для новых CSS подсказок
        $bar.attr('data-tooltip', `${$bar.data('strategy')}: ${newSignal.toUpperCase()}`);
        
        // Обновляем размеры с увеличенной максимальной высотой
        if (newSignal === 'hold') {
          $bar.css({
            'width': '6px',
            'height': '6px',
            'border-radius': '50%'
          });
        } else {
          // Увеличиваем максимальную высоту до 100px
          const height = Math.max(20, Math.min(100, weight * 120));
          $bar.css({
            'width': '8px',
            'height': `${height}px`,
            'border-radius': '4px',
            'max-height': '100px'
          });
        }
        
        // Убираем класс анимации
        setTimeout(() => {
          $bar.removeClass('updating');
        }, 400);
      }
    },

    // Публичные методы
    refresh: function() {
      this.updateVotingAnimation();
    },

    // Принудительное обновление с новыми данными
    updateWithData: function(signals) {
      this.updateBars(signals);
    },
    
    // Функция для очистки ресурсов
    cleanup: function() {
      try {
        // Очищаем все таймеры
        if (this._updateTimer) {
          clearInterval(this._updateTimer);
          this._updateTimer = null;
        }
        
        // Очищаем контейнер
        if (this.container && this.container.length) {
          this.container.empty();
        }
        
        console.log('Strategy Voting модуль очищен');
      } catch (e) {
        console.warn('Ошибка при очистке Strategy Voting модуля:', e);
      }
    }
  };

  // Добавляем в глобальный App объект
  window.App.strategyVoting = StrategyVoting;

  // Инициализация при готовности DOM
  // Убираем автоматическую инициализацию, так как она будет вызвана из app_init.js
  // $(document).ready(function() {
  //   StrategyVoting.init();
  // });

  // Экспорт для использования в других модулях
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = StrategyVoting;
  }
})();
