# ⚡ Быстрый старт локального тестирования

## 🎯 За 3 минуты от идеи до работающей системы

### 1. Проверка окружения

```bash
# Убедитесь, что вы в корне проекта
ls docker-compose-local-test.yml

# Проверьте Docker
docker --version
docker-compose --version
```

### 2. Запуск системы

#### Linux/macOS:

```bash
chmod +x deploy/test-local.sh
./deploy/test-local.sh start
```

#### Windows:

```powershell
.\deploy\test-local.ps1 start
```

**Готово!** 🎉

## 🔍 Проверка работы

```bash
# Статус всех сервисов
./deploy/test-local.sh status

# Открыть дашборд
# http://localhost:8501
```

## 🧪 Тест изоляции

```bash
# Перезапустить только RSI стратегию
./deploy/test-local.sh test-strategy ft-rsi

# Проверить, что остальные работают
./deploy/test-local.sh status
```

## 📊 Что запущено

- **6 стратегий** в отдельных Docker контейнерах
- **Изолированные данные** для каждой стратегии
- **Streamlit дашборд** на порту 8501
- **Автоматический restart** при сбоях

## 🚨 Если что-то пошло не так

```bash
# Остановить все
./deploy/test-local.sh stop

# Просмотреть логи
./deploy/test-local.sh logs

# Перезапустить
./deploy/test-local.sh restart
```

## 🔄 Переход к продакшену

После успешного тестирования:

```bash
# На сервере
./deploy/setup-server.sh

# На локальной машине
./deploy/setup-local.sh setup-ssh freqtrader your-server-ip
./deploy/setup-local.sh add-remote freqtrader your-server-ip
./deploy/setup-local.sh deploy
```

---

**🎯 Цель достигнута: Локальное тестирование системы с изолированными стратегиями!**
