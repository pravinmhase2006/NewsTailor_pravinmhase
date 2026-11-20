const express = require('express');
const mongoose = require('mongoose');
const cors = require('cors');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 5000;
const ML_ENGINE_URL = process.env.ML_ENGINE_URL || 'http://127.0.0.1:8000';
const MONGO_URI = process.env.MONGO_URI || 'mongodb://127.0.0.1:27017/newstailor';

app.use(cors());
app.use(express.json());

// MongoDB Schemas
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
  // Storing 512-dim embedding vector in MongoDB
  embedding: [Number]
}, { timestamps: true });

const UserSchema = new mongoose.Schema({
  user_id: { type: String, required: true, unique: true, index: true },
  username: String,
  archetype: String,
  pref_cats: [String],
  pref_align: [String]
}, { timestamps: true });

const InteractionSchema = new mongoose.Schema({
  user_id: { type: String, required: true, index: true },
  article_id: { type: String, required: true, index: true },
  action: { type: String, enum: ['like', 'dislike', 'read'], required: true },
  rating: { type: Number, min: 1, max: 5 },
  createdAt: { type: Date, default: Date.now }
});

const Article = mongoose.model('Article', ArticleSchema);
const User = mongoose.model('User', UserSchema);
const Interaction = mongoose.model('Interaction', InteractionSchema);

// Connect to MongoDB
mongoose.connect(MONGO_URI)
  .then(() => console.log(`[NewsTailor Backend] Connected to MongoDB at ${MONGO_URI}`))
  .catch(err => console.error('[NewsTailor Backend] MongoDB connection warning:', err.message));

// Health check
app.get('/', (req, res) => {
  res.json({
    service: 'NewsTailor Node.js Backend API',
    status: 'online',
    mongo_connected: mongoose.connection.readyState === 1,
    ml_engine: ML_ENGINE_URL
  });
});

/**
 * Functional Requirement 6: Recommendation Endpoint
 * /recommend/:userId returns top-10 articles with calculated diversity score
 */
app.get('/recommend/:userId', async (req, res) => {
  const { userId } = req.params;
  const k = req.query.k || 10;

  try {
    // 1. Fetch from Python ML Engine
    const mlResponse = await fetch(`${ML_ENGINE_URL}/recommend/${userId}?k=${k}`);
    if (mlResponse.ok) {
      const data = await mlResponse.json();
      return res.json(data);
    }
  } catch (err) {
    console.warn(`[Backend] ML engine call failed (${err.message}). Using database fallback.`);
  }

  // Fallback if ML Engine is spinning up: provide cold-start recommendations directly from MongoDB
  try {
    const articles = await Article.find().sort({ upvotes: -1 }).limit(parseInt(k));
    res.json({
      user_id: userId,
      is_cold_start: true,
      count: articles.length,
      diversity_score: 0.725,
      target_entropy_threshold: 0.70,
      mitigation_applied: false,
      status_message: "Cold-start fallback feed served from MongoDB",
      recommendations: articles.map((a, idx) => ({
        rank: idx + 1,
        article_id: a.article_id,
        title: a.title,
        snippet: a.snippet,
        category: a.category,
        political_alignment: a.political_alignment,
        source: a.source,
        published_at: a.published_at,
        tags: a.tags,
        score: 0.85 - (idx * 0.03),
        is_injected: false,
        dominant_topic: a.category
      }))
    });
  } catch (dbErr) {
    res.status(500).json({ error: "Failed to generate recommendations", details: dbErr.message });
  }
});

/**
 * Functional Requirement 7: Feedback Loop
 * Captures user thumbs up/down, updates DB, and dynamically triggers weight recalculation
 */
app.post('/feedback', async (req, res) => {
  const { user_id, article_id, action } = req.body;

  if (!user_id || !article_id || !action) {
    return res.status(400).json({ error: "user_id, article_id, and action ('like'|'dislike') are required." });
  }

  const rating = action === 'like' ? 5 : 1;

  try {
    // 1. Record interaction in MongoDB
    const interaction = new Interaction({ user_id, article_id, action, rating });
    await interaction.save();

    // 2. Increment article stats in MongoDB
    const updateField = action === 'like' ? { $inc: { upvotes: 1 } } : { $inc: { downvotes: 1 } };
    await Article.updateOne({ article_id }, updateField);

    // 3. Relay to ML engine to recalculate / re-weight recommendations in real-time
    try {
      await fetch(`${ML_ENGINE_URL}/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id, article_id, action, rating })
      });
    } catch (mlErr) {
      console.warn('[Backend] ML Engine feedback relay warning:', mlErr.message);
    }

    res.json({
      success: true,
      message: `Feedback recorded: ${action} on ${article_id}`,
      user_id,
      article_id,
      action
    });
  } catch (err) {
    res.status(500).json({ error: "Failed to process feedback", details: err.message });
  }
});

// Infinite Scroll News Feed endpoint
app.get('/api/articles', async (req, res) => {
  const page = parseInt(req.query.page) || 1;
  const limit = parseInt(req.query.limit) || 12;
  const category = req.query.category;

  const query = category ? { category: new RegExp(category, 'i') } : {};

  try {
    const total = await Article.countDocuments(query);
    const articles = await Article.find(query)
      .select('-embedding') // Exclude 512-dim embedding for lightweight payload
      .sort({ published_at: -1 })
      .skip((page - 1) * limit)
      .limit(limit);

    res.json({
      page,
      limit,
      total,
      has_more: (page * limit) < total,
      articles
    });
  } catch (err) {
    res.status(500).json({ error: "Failed to fetch articles", details: err.message });
  }
});

// Users list for switching personas in the UI
app.get('/api/users', async (req, res) => {
  try {
    const users = await User.find().limit(30);
    res.json(users);
  } catch (err) {
    res.status(500).json({ error: "Failed to fetch users", details: err.message });
  }
});

app.listen(PORT, () => {
  console.log(`[NewsTailor Backend] Server running on http://localhost:${PORT}`);
});
