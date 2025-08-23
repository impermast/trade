// Module Loader - система управления загрузкой модулей
(function(){
  // Проверяем, что core уже загружен
  if (!window.App || !window.App.ModuleManager) {
    console.error('❌ Module Loader: Core модуль не загружен!');
    return;
  }

  const ModuleManager = window.App.ModuleManager;
  const DependencyManager = window.App.DependencyManager;

  // Система загрузки модулей
  const ModuleLoader = {
    // Статус загрузки модулей
    moduleStatus: {},
    
    // Очередь загрузки
    loadQueue: [],
    
    // Зарегистрированные модули
    registeredModules: {},
    
    // Регистрация модуля
    registerModule: function(name, module, dependencies = []) {
      this.registeredModules[name] = {
        module: module,
        dependencies: dependencies,
        loaded: false,
        error: null
      };
      
      console.log(`📦 Module Loader: Модуль ${name} зарегистрирован`);
      
      // Добавляем в очередь загрузки
      this.addToLoadQueue(name);
    },
    
    // Добавление в очередь загрузки
    addToLoadQueue: function(moduleName) {
      if (!this.loadQueue.includes(moduleName)) {
        this.loadQueue.push(moduleName);
      }
    },
    
    // Проверка готовности зависимостей модуля
    checkModuleDependencies: function(moduleName) {
      const moduleInfo = this.registeredModules[moduleName];
      if (!moduleInfo) return false;
      
      // Проверяем внешние зависимости
      for (const dep of moduleInfo.dependencies) {
        if (!DependencyManager.checkDependency(dep)) {
          return false;
        }
      }
      
      // Проверяем внутренние зависимости модулей
      const internalDeps = this.getInternalDependencies(moduleName);
      for (const dep of internalDeps) {
        if (!this.isModuleLoaded(dep)) {
          return false;
        }
      }
      
      return true;
    },
    
    // Получение внутренних зависимостей модуля
    getInternalDependencies: function(moduleName) {
      const dependencies = {
        'theme': [],
        'ui': ['theme'],
        'state': ['ui'],
        'apiInfo': ['ui'],
        'chart': ['ui', 'state'],
        'logs': ['ui'],
        'csv': ['ui'],
        'kpi': ['ui', 'state'],
        'strategyVoting': ['ui', 'state'],
        'init': ['theme', 'ui', 'state', 'apiInfo', 'chart', 'logs', 'csv', 'kpi', 'strategyVoting']
      };
      
      return dependencies[moduleName] || [];
    },
    
    // Проверка загрузки модуля
    isModuleLoaded: function(moduleName) {
      return this.registeredModules[moduleName]?.loaded || false;
    },
    
    // Загрузка модуля
    loadModule: async function(moduleName) {
      const moduleInfo = this.registeredModules[moduleName];
      if (!moduleInfo || moduleInfo.loaded) {
        return true;
      }
      
      try {
        console.log(`🔄 Module Loader: Загружаем модуль ${moduleName}...`);
        
        // Проверяем зависимости
        if (!this.checkModuleDependencies(moduleName)) {
          console.log(`⏳ Module Loader: Модуль ${moduleName} ждет зависимости...`);
          return false;
        }
        
        // Инициализируем модуль
        if (moduleInfo.module && typeof moduleInfo.module.init === 'function') {
          await moduleInfo.module.init();
        }
        
        // Помечаем как загруженный
        moduleInfo.loaded = true;
        moduleInfo.error = null;
        
        console.log(`✅ Module Loader: Модуль ${moduleName} успешно загружен`);
        
        // Проверяем, можем ли загрузить другие модули
        this.processLoadQueue();
        
        return true;
        
      } catch (error) {
        console.error(`❌ Module Loader: Ошибка загрузки модуля ${moduleName}:`, error);
        moduleInfo.error = error;
        return false;
      }
    },
    
    // Обработка очереди загрузки
    processLoadQueue: function() {
      let loadedAny = false;
      
      for (let i = 0; i < this.loadQueue.length; i++) {
        const moduleName = this.loadQueue[i];
        
        if (this.checkModuleDependencies(moduleName)) {
          this.loadModule(moduleName);
          this.loadQueue.splice(i, 1);
          i--;
          loadedAny = true;
        }
      }
      
      // Если ничего не загрузилось, но очередь не пуста, ждем
      if (!loadedAny && this.loadQueue.length > 0) {
        setTimeout(() => {
          this.processLoadQueue();
        }, 100);
      }
      
      // Проверяем, все ли модули загружены
      this.checkAllModulesLoaded();
    },
    
    // Проверка загрузки всех модулей
    checkAllModulesLoaded: function() {
      const allLoaded = Object.values(this.registeredModules).every(m => m.loaded);
      
      if (allLoaded) {
        console.log('🎉 Module Loader: Все модули загружены!');
        
        // Уведомляем о готовности
        window.dispatchEvent(new CustomEvent('allModulesLoaded'));
        
        // Запускаем инициализацию дашборда
        if (ModuleManager && ModuleManager.executeInit) {
          ModuleManager.executeInit();
        }
      }
    },
    
    // Получение статуса загрузки
    getLoadStatus: function() {
      const status = {};
      
      for (const [name, info] of Object.entries(this.registeredModules)) {
        status[name] = {
          loaded: info.loaded,
          error: info.error,
          dependencies: info.dependencies
        };
      }
      
      return status;
    },
    
    // Принудительная загрузка модуля (для отладки)
    forceLoadModule: function(moduleName) {
      console.warn(`⚠️ Module Loader: Принудительная загрузка модуля ${moduleName}`);
      return this.loadModule(moduleName);
    },
    
    // Очистка ресурсов
    cleanup: function() {
      this.moduleStatus = {};
      this.loadQueue = [];
      this.registeredModules = {};
    }
  };

  // Автоматическая регистрация модулей при их появлении
  const autoRegisterModules = () => {
    const moduleNames = ['theme', 'ui', 'state', 'apiInfo', 'chart', 'logs', 'csv', 'kpi', 'strategyVoting'];
    
    moduleNames.forEach(name => {
      if (window.App[name] && !ModuleLoader.registeredModules[name]) {
        console.log(`🔍 Module Loader: Авторегистрация модуля ${name}`);
        ModuleLoader.registerModule(name, window.App[name]);
      }
    });
  };

  // Проверяем модули каждые 100мс
  const checkInterval = setInterval(() => {
    autoRegisterModules();
    
    // Если все модули зарегистрированы, останавливаем проверку
    const allRegistered = moduleNames.every(name => 
      ModuleLoader.registeredModules[name] || window.App[name]
    );
    
    if (allRegistered) {
      clearInterval(checkInterval);
      console.log('✅ Module Loader: Все модули зарегистрированы, начинаем загрузку...');
      ModuleLoader.processLoadQueue();
    }
  }, 100);

  // Экспортируем ModuleLoader в глобальный App
  window.App.ModuleLoader = ModuleLoader;
  
  console.log('🚀 Module Loader инициализирован');

})();
