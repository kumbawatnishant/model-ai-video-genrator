const { Sequelize, DataTypes } = require('sequelize');

let sequelize;
if (process.env.DATABASE_URL) {
  // Production / Render (PostgreSQL)
  sequelize = new Sequelize(process.env.DATABASE_URL, {
    dialect: 'postgres',
    logging: false,
    dialectOptions: {
      ssl: {
        require: true,
        rejectUnauthorized: false // Required for Render's self-signed certs
      }
    }
  });
} else {
  // Local Development (SQLite in-memory)
  sequelize = new Sequelize({
    dialect: 'sqlite',
    storage: ':memory:',
    logging: false
  });
}

const User = sequelize.define('User', {
  id: { type: DataTypes.INTEGER, primaryKey: true, autoIncrement: true },
  email: { type: DataTypes.STRING, unique: true, allowNull: false },
  passwordHash: { type: DataTypes.STRING, allowNull: false },
  refreshToken: { type: DataTypes.TEXT, allowNull: true }
});

const ApiKey = sequelize.define('ApiKey', {
  id: { type: DataTypes.UUID, defaultValue: DataTypes.UUIDV4, primaryKey: true },
  provider: { type: DataTypes.STRING, allowNull: false },
  key: { type: DataTypes.TEXT, allowNull: false },
  meta: { type: DataTypes.JSON, allowNull: true },
  last_tested: { type: DataTypes.DATE, allowNull: true }
});

const Subscription = sequelize.define('Subscription', {
  id: { type: DataTypes.UUID, defaultValue: DataTypes.UUIDV4, primaryKey: true },
  plan_id: { type: DataTypes.STRING, allowNull: false },
  status: { type: DataTypes.STRING, allowNull: false },
  tier: { type: DataTypes.STRING, allowNull: true },
  quotas: { type: DataTypes.JSON, allowNull: true },
  next_billing_at: { type: DataTypes.DATE, allowNull: true }
});

User.hasMany(ApiKey, { as: 'apiKeys' });
ApiKey.belongsTo(User);

User.hasOne(Subscription, { as: 'subscription' });
Subscription.belongsTo(User);

async function initDb() {
  await sequelize.authenticate();
  await sequelize.sync();
}

module.exports = { sequelize, User, ApiKey, Subscription, initDb };
