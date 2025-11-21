-- Схема базы данных для сервиса подбора лотерей Столото

-- Удаление существующих таблиц (если нужно пересоздать)
DROP TABLE IF EXISTS chat_history CASCADE;
DROP TABLE IF EXISTS recommendations CASCADE;
DROP TABLE IF EXISTS user_stats CASCADE;
DROP TABLE IF EXISTS user_preferences CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS prize_categories CASCADE;
DROP TABLE IF EXISTS draws CASCADE;
DROP TABLE IF EXISTS lotteries CASCADE;

-- Таблица лотерей
CREATE TABLE lotteries (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL,
    lottery_type VARCHAR(50) NOT NULL CHECK (lottery_type IN ('instant', 'draw')), -- мгновенная или тиражная
    ticket_price DECIMAL(10, 2) NOT NULL,
    draw_frequency VARCHAR(100), -- частота розыгрышей (например, "ежедневно", "2 раза в неделю")
    description TEXT,
    rules TEXT,
    max_prize DECIMAL(15, 2), -- максимальный приз
    url VARCHAR(500),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Индексы для лотерей
CREATE INDEX idx_lotteries_type ON lotteries(lottery_type);
CREATE INDEX idx_lotteries_active ON lotteries(is_active);
CREATE INDEX idx_lotteries_price ON lotteries(ticket_price);

-- Таблица тиражей
CREATE TABLE draws (
    id SERIAL PRIMARY KEY,
    lottery_id INTEGER REFERENCES lotteries(id) ON DELETE CASCADE,
    draw_number INTEGER NOT NULL,
    draw_date DATE NOT NULL,
    winning_numbers TEXT, -- JSON или строка с выигрышными номерами
    total_prize_fund DECIMAL(15, 2),
    winners_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(lottery_id, draw_number)
);

-- Индексы для тиражей
CREATE INDEX idx_draws_lottery ON draws(lottery_id);
CREATE INDEX idx_draws_date ON draws(draw_date);

-- Таблица категорий призов
CREATE TABLE prize_categories (
    id SERIAL PRIMARY KEY,
    lottery_id INTEGER REFERENCES lotteries(id) ON DELETE CASCADE,
    draw_id INTEGER REFERENCES draws(id) ON DELETE CASCADE,
    category_name VARCHAR(100) NOT NULL, -- например, "Джекпот", "5 из 6", "4 из 6"
    prize_amount DECIMAL(15, 2),
    winners_count INTEGER DEFAULT 0,
    probability DECIMAL(10, 8), -- вероятность выигрыша в этой категории
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Индексы для категорий призов
CREATE INDEX idx_prize_categories_lottery ON prize_categories(lottery_id);
CREATE INDEX idx_prize_categories_draw ON prize_categories(draw_id);

-- Таблица пользователей
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

-- Индекс для пользователей
CREATE INDEX idx_users_email ON users(email);

-- Таблица предпочтений пользователя
CREATE TABLE user_preferences (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    budget DECIMAL(10, 2), -- бюджет на участие
    preferred_prize_type VARCHAR(50), -- тип выигрыша: 'instant', 'draw', 'both'
    preferred_prize_size VARCHAR(50), -- величина приза: 'small', 'medium', 'large', 'jackpot'
    min_acceptable_probability DECIMAL(10, 8), -- минимально приемлемая вероятность
    max_waiting_time VARCHAR(50), -- максимальное время ожидания розыгрыша
    risk_profile VARCHAR(50), -- профиль риска: 'conservative', 'moderate', 'aggressive'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id)
);

-- Таблица статистики пользователя
CREATE TABLE user_stats (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    total_games_played INTEGER DEFAULT 0,
    total_spent DECIMAL(15, 2) DEFAULT 0,
    total_won DECIMAL(15, 2) DEFAULT 0,
    win_rate DECIMAL(5, 2) DEFAULT 0, -- процент выигрышей
    favorite_lottery_id INTEGER REFERENCES lotteries(id) ON DELETE SET NULL,
    last_game_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id)
);

-- Таблица рекомендаций
CREATE TABLE recommendations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    lottery_id INTEGER REFERENCES lotteries(id) ON DELETE CASCADE,
    score DECIMAL(5, 2) NOT NULL, -- скоринг лотереи для пользователя (0-100)
    explanation TEXT, -- объяснение рекомендации
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Индексы для рекомендаций
CREATE INDEX idx_recommendations_user ON recommendations(user_id);
CREATE INDEX idx_recommendations_lottery ON recommendations(lottery_id);
CREATE INDEX idx_recommendations_score ON recommendations(score DESC);

-- Таблица истории чата
CREATE TABLE chat_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    message TEXT NOT NULL,
    is_user_message BOOLEAN NOT NULL, -- TRUE если от пользователя, FALSE если от бота
    context_data JSONB, -- дополнительный контекст (используемые данные из БД)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Индексы для истории чата
CREATE INDEX idx_chat_history_user ON chat_history(user_id);
CREATE INDEX idx_chat_history_created ON chat_history(created_at DESC);

-- Создание представления для сводной статистики
CREATE OR REPLACE VIEW lottery_statistics AS
SELECT 
    l.id,
    l.name,
    l.lottery_type,
    l.ticket_price,
    COUNT(DISTINCT d.id) as total_draws,
    AVG(d.total_prize_fund) as avg_prize_fund,
    MAX(d.total_prize_fund) as max_prize_fund,
    SUM(d.winners_count) as total_winners,
    AVG(pc.probability) as avg_win_probability
FROM 
    lotteries l
    LEFT JOIN draws d ON l.id = d.lottery_id
    LEFT JOIN prize_categories pc ON l.id = pc.lottery_id
WHERE 
    l.is_active = TRUE
GROUP BY 
    l.id, l.name, l.lottery_type, l.ticket_price;

-- Комментарии к таблицам
COMMENT ON TABLE lotteries IS 'Основная информация о лотереях';
COMMENT ON TABLE draws IS 'Результаты тиражей лотерей';
COMMENT ON TABLE prize_categories IS 'Категории призов и их вероятности';
COMMENT ON TABLE users IS 'Пользователи системы';
COMMENT ON TABLE user_preferences IS 'Предпочтения пользователей для персонализации';
COMMENT ON TABLE user_stats IS 'Статистика игр пользователей';
COMMENT ON TABLE recommendations IS 'История рекомендаций';
COMMENT ON TABLE chat_history IS 'История диалогов с чат-ботом';
