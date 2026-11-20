const mongoose = require('mongoose');
const fs = require('fs');
const path = require('path');

const MONGO_URI = process.env.MONGO_URI || 'mongodb://127.0.0.1:27017/newstailor';

const ArticleSchema = new mongoose.Schema({
  article_id: { type: String, required: true, unique: true, index: true },
  title: { type: String, required: true },
  snippet: String,
  content: String,
  category: { type: String, index: true },
  political_alignment: { type: String, index: true },
  source: String,
  published_at: Date,
  tags: [String],
  reads_count: { type: Number, default: 0 },
  upvotes: { type: Number, default: 0 },
  downvotes: { type: Number, default: 0 },
  embedding: [Number]
});

const UserSchema = new mongoose.Schema({
  user_id: { type: String, required: true, unique: true, index: true },
  username: String,
  archetype: String,
  pref_cats: [String],
  pref_align: [String]
});

const Article = mongoose.model('Article', ArticleSchema);
const User = mongoose.model('User', UserSchema);

async function seedDatabase() {
  console.log(`Connecting to MongoDB at ${MONGO_URI}...`);
  await mongoose.connect(MONGO_URI);
  console.log('Connected to MongoDB.');

  const articlesPath = path.join(__dirname, '..', 'ml_engine', 'articles_10k.json');
  const usersPath = path.join(__dirname, '..', 'ml_engine', 'users.json');

  if (!fs.existsSync(articlesPath)) {
    console.error(`Articles file not found at ${articlesPath}. Run ml_engine pipeline first.`);
    process.exit(1);
  }

  console.log('Loading articles JSON...');
  const articles = JSON.parse(fs.readFileSync(articlesPath, 'utf8'));

  console.log(`Found ${articles.length} articles. Seeding to MongoDB...`);
  await Article.deleteMany({});

  // Batch insert in chunks of 1000
  const chunkSize = 1000;
  for (let i = 0; i < articles.length; i += chunkSize) {
    const chunk = articles.slice(i, i + chunkSize).map(a => ({
      article_id: a.id,
      title: a.title,
      snippet: a.snippet,
      content: a.content,
      category: a.category,
      political_alignment: a.political_alignment,
      source: a.source,
      published_at: new Date(a.published_at),
      tags: a.tags,
      reads_count: a.reads_count,
      upvotes: a.upvotes,
      downvotes: a.downvotes
    }));
    await Article.insertMany(chunk);
    console.log(`Seeded ${Math.min(i + chunkSize, articles.length)} / ${articles.length} articles into MongoDB`);
  }

  if (fs.existsSync(usersPath)) {
    console.log('Seeding users...');
    const users = JSON.parse(fs.readFileSync(usersPath, 'utf8'));
    await User.deleteMany({});
    await User.insertMany(users);
    console.log(`Seeded ${users.length} users into MongoDB`);
  }

  console.log('MongoDB Seeding complete!');
  process.exit(0);
}

seedDatabase().catch(err => {
  console.error('Seeding error:', err);
  process.exit(1);
});
