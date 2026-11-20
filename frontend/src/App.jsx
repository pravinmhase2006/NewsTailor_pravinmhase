import React, { useState, useEffect, useRef } from 'react';
import { 
  ThumbsUp, 
  ThumbsDown, 
  ShieldCheck, 
  Sparkles, 
  RefreshCw, 
  UserCheck, 
  TrendingUp, 
  Layers, 
  Compass, 
  Filter, 
  Info,
  CheckCircle2,
  AlertTriangle
} from 'lucide-react';

const PRESET_USERS = [
  { id: 'usr_0001', name: 'Reader 1: Tech Enthusiast', pref: 'AI, Computing, Hardware' },
  { id: 'usr_0002', name: 'Reader 2: Progressive Eco-Advocate', pref: 'Climate, Clean Energy, Left Politics' },
  { id: 'usr_0003', name: 'Reader 3: Market Conservative', pref: 'Finance, Fiscal Policy, Right Politics' },
  { id: 'usr_0004', name: 'Reader 4: Global Diplomat', pref: 'World Affairs, Trade, Geopolitics' },
  { id: 'usr_cold_start', name: 'New Reader (Cold Start)', pref: 'Zero historical interactions' },
];

const CATEGORIES = ['All', 'Politics', 'Technology', 'Economy & Finance', 'Climate & Environment', 'Healthcare & Science', 'World & Diplomacy'];

export default function App() {
  const [currentUser, setCurrentUser] = useState(PRESET_USERS[0].id);
  const [recommendations, setRecommendations] = useState([]);
  const [diversityData, setDiversityData] = useState(null);
  const [loadingRecs, setLoadingRecs] = useState(false);
  const [userVotes, setUserVotes] = useState({});
  const [notification, setNotification] = useState(null);

  // Infinite scroll articles
  const [articles, setArticles] = useState([]);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [activeCategory, setActiveCategory] = useState('All');
  const [activeTab, setActiveTab] = useState('recommendations'); // 'recommendations' | 'explore'

  const observerRef = useRef();

  // Load recommendations for the current user
  const fetchRecommendations = async (userId) => {
    setLoadingRecs(true);
    try {
      const res = await fetch(`/recommend/${userId}?k=10`);
      if (res.ok) {
        const data = await res.json();
        setRecommendations(data.recommendations || []);
        setDiversityData({
          score: data.diversity_score,
          threshold: data.target_entropy_threshold,
          mitigationApplied: data.mitigation_applied,
          statusMessage: data.status_message,
          topicDistribution: data.topic_distribution || [],
          isColdStart: data.is_cold_start
        });
      }
    } catch (err) {
      console.error('Failed to load recommendations:', err);
    } finally {
      setLoadingRecs(false);
    }
  };

  // Load infinite scroll articles
  const fetchArticles = async (pageNum, category = activeCategory, reset = false) => {
    if (loadingMore) return;
    setLoadingMore(true);
    try {
      const catParam = category === 'All' ? '' : `&category=${encodeURIComponent(category)}`;
      const res = await fetch(`/api/articles?page=${pageNum}&limit=10${catParam}`);
      if (res.ok) {
        const data = await res.json();
        if (reset) {
          setArticles(data.articles || []);
        } else {
          setArticles(prev => [...prev, ...(data.articles || [])]);
        }
        setHasMore(data.has_more);
      }
    } catch (err) {
      console.error('Failed to load infinite articles:', err);
    } finally {
      setLoadingMore(false);
    }
  };

  useEffect(() => {
    fetchRecommendations(currentUser);
  }, [currentUser]);

  useEffect(() => {
    setPage(1);
    fetchArticles(1, activeCategory, true);
  }, [activeCategory]);

  // Handle upvote / downvote feedback
  const handleVote = async (articleId, action) => {
    const prevVote = userVotes[articleId];
    if (prevVote === action) return; // already voted

    setUserVotes(prev => ({ ...prev, [articleId]: action }));

    try {
      const res = await fetch('/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: currentUser,
          article_id: articleId,
          action: action
        })
      });

      if (res.ok) {
        const data = await res.json();
        showNotification(
          action === 'like' 
            ? '👍 Upvote recorded! Collaborative & Content weights re-calculated in real-time.' 
            : '👎 Downvote recorded! Article de-prioritized in future recommendation slates.'
        );
      }
    } catch (err) {
      console.error('Feedback submission failed:', err);
    }
  };

  const showNotification = (msg) => {
    setNotification(msg);
    setTimeout(() => setNotification(null), 4000);
  };

  const getAlignmentBadge = (align) => {
    switch (align) {
      case 'Left':
        return 'bg-blue-900/60 text-blue-300 border-blue-700/60';
      case 'Center-Left':
        return 'bg-cyan-900/60 text-cyan-300 border-cyan-700/60';
      case 'Center':
        return 'bg-purple-900/60 text-purple-300 border-purple-700/60';
      case 'Center-Right':
        return 'bg-orange-900/60 text-orange-300 border-orange-700/60';
      case 'Right':
        return 'bg-rose-900/60 text-rose-300 border-rose-700/60';
      default:
        return 'bg-slate-800 text-slate-300 border-slate-700';
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      {/* Toast Notification */}
      {notification && (
        <div className="fixed bottom-6 right-6 z-50 bg-sky-600 text-white px-5 py-3 rounded-xl shadow-2xl flex items-center space-x-3 border border-sky-400/40 animate-bounce">
          <CheckCircle2 className="w-5 h-5 flex-shrink-0" />
          <span className="text-sm font-medium">{notification}</span>
        </div>
      )}

      {/* Top Header */}
      <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 py-3 sm:px-6 lg:px-8 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-sky-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-sky-500/20">
              <Compass className="w-6 h-6 text-white" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h1 className="text-xl font-bold tracking-tight text-white">NewsTailor</h1>
                <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-sky-500/10 text-sky-400 border border-sky-500/30">
                  Hybrid RecSys + Bias Mitigation
                </span>
              </div>
              <p className="text-xs text-slate-400">Sentence-BERT (512-dim) • FAISS ANN • SVD (Surprise) • LDA Topic Model</p>
            </div>
          </div>

          {/* User Persona Switcher */}
          <div className="flex items-center space-x-3 bg-slate-800/80 border border-slate-700/80 rounded-xl p-1.5 shadow-inner">
            <UserCheck className="w-4 h-4 text-sky-400 ml-2" />
            <select
              value={currentUser}
              onChange={(e) => setCurrentUser(e.target.value)}
              className="bg-transparent text-sm font-medium text-slate-200 outline-none pr-4 cursor-pointer"
            >
              {PRESET_USERS.map(u => (
                <option key={u.id} value={u.id} className="bg-slate-900 text-slate-200">
                  {u.name}
                </option>
              ))}
            </select>
            <button
              onClick={() => fetchRecommendations(currentUser)}
              title="Refresh Recommendations"
              className="p-1.5 rounded-lg hover:bg-slate-700 text-slate-400 hover:text-white transition"
            >
              <RefreshCw className={`w-4 h-4 ${loadingRecs ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 flex-1 w-full space-y-6">
        {/* Bias Mitigation & Diversity Dashboard Banner */}
        {diversityData && (
          <div className="bg-gradient-to-r from-slate-900 via-slate-900/90 to-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl relative overflow-hidden">
            <div className="absolute top-0 right-0 w-96 h-96 bg-sky-500/5 rounded-full blur-3xl pointer-events-none"></div>

            <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 relative z-10">
              <div className="space-y-2">
                <div className="flex items-center space-x-2">
                  <ShieldCheck className={`w-5 h-5 ${diversityData.score >= 0.70 ? 'text-emerald-400' : 'text-amber-400'}`} />
                  <span className="text-sm font-semibold tracking-wide uppercase text-slate-300">
                    Algorithmic Bias Mitigation System
                  </span>
                  {diversityData.mitigationApplied && (
                    <span className="px-2.5 py-0.5 text-xs font-bold rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                      Diversity Injected
                    </span>
                  )}
                  {diversityData.isColdStart && (
                    <span className="px-2.5 py-0.5 text-xs font-bold rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/40">
                      Cold-Start Activated
                    </span>
                  )}
                </div>
                <p className="text-sm text-slate-300 max-w-2xl">
                  {diversityData.statusMessage}
                </p>
                <div className="flex items-center space-x-4 text-xs text-slate-400 pt-1">
                  <span>Weight Blend: <strong className="text-slate-200">70% Collaborative Filtering</strong> (SVD) + <strong className="text-slate-200">30% Content-Based</strong> (FAISS)</span>
                  <span>•</span>
                  <span>Target Entropy: <strong className="text-emerald-400">&gt; 0.70</strong></span>
                </div>
              </div>

              {/* Entropy Gauge */}
              <div className="flex items-center space-x-6 bg-slate-950/60 border border-slate-800 rounded-xl p-4 min-w-[280px]">
                <div className="space-y-1 flex-1">
                  <div className="flex justify-between text-xs font-semibold">
                    <span className="text-slate-400">Diversity Entropy</span>
                    <span className={`font-mono ${diversityData.score >= 0.70 ? 'text-emerald-400 font-bold' : 'text-amber-400'}`}>
                      {diversityData.score.toFixed(3)} / 1.000
                    </span>
                  </div>
                  <div className="w-full h-2.5 bg-slate-800 rounded-full overflow-hidden">
                    <div 
                      className={`h-full rounded-full transition-all duration-700 ${
                        diversityData.score >= 0.70 
                          ? 'bg-gradient-to-r from-teal-400 to-emerald-500 shadow-lg shadow-emerald-500/30' 
                          : 'bg-gradient-to-r from-amber-400 to-orange-500'
                      }`}
                      style={{ width: `${Math.min(100, Math.max(10, diversityData.score * 100))}%` }}
                    />
                  </div>
                  <div className="flex justify-between text-[10px] text-slate-500">
                    <span>Echo Chamber (0.0)</span>
                    <span className="text-emerald-400 font-semibold">Target (0.70)</span>
                    <span>Max Diverse (1.0)</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* View Tabs */}
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex space-x-2">
            <button
              onClick={() => setActiveTab('recommendations')}
              className={`px-4 py-2 rounded-xl text-sm font-semibold transition flex items-center space-x-2 ${
                activeTab === 'recommendations'
                  ? 'bg-sky-500 text-white shadow-lg shadow-sky-500/25'
                  : 'text-slate-400 hover:text-white hover:bg-slate-900'
              }`}
            >
              <Sparkles className="w-4 h-4" />
              <span>Recommended For You (Top 10)</span>
            </button>
            <button
              onClick={() => setActiveTab('explore')}
              className={`px-4 py-2 rounded-xl text-sm font-semibold transition flex items-center space-x-2 ${
                activeTab === 'explore'
                  ? 'bg-sky-500 text-white shadow-lg shadow-sky-500/25'
                  : 'text-slate-400 hover:text-white hover:bg-slate-900'
              }`}
            >
              <Compass className="w-4 h-4" />
              <span>Infinite News Feed</span>
            </button>
          </div>

          {activeTab === 'explore' && (
            <div className="flex items-center space-x-2 overflow-x-auto py-1">
              {CATEGORIES.map(cat => (
                <button
                  key={cat}
                  onClick={() => setActiveCategory(cat)}
                  className={`px-3 py-1 rounded-lg text-xs font-medium transition ${
                    activeCategory === cat
                      ? 'bg-slate-700 text-white'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                  }`}
                >
                  {cat}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* TAB 1: RECOMMENDATIONS */}
        {activeTab === 'recommendations' && (
          <div className="space-y-4">
            {loadingRecs ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {[1, 2, 3, 4, 5, 6].map(n => (
                  <div key={n} className="h-44 bg-slate-900/60 rounded-2xl animate-pulse border border-slate-800 p-5 space-y-3">
                    <div className="h-4 bg-slate-800 rounded w-1/3"></div>
                    <div className="h-6 bg-slate-800 rounded w-4/5"></div>
                    <div className="h-10 bg-slate-800 rounded w-full"></div>
                  </div>
                ))}
              </div>
            ) : recommendations.length === 0 ? (
              <div className="text-center py-16 text-slate-500 space-y-2">
                <AlertTriangle className="w-10 h-10 mx-auto text-amber-500" />
                <p className="text-base font-medium">No recommendations loaded yet.</p>
                <p className="text-xs">Ensure the backend and ML engine services are running.</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {recommendations.map((item, index) => {
                  const vote = userVotes[item.article_id];
                  const isInjected = item.is_injected;

                  return (
                    <article
                      key={item.article_id}
                      className={`relative rounded-2xl p-5 border transition-all duration-200 flex flex-col justify-between ${
                        isInjected
                          ? 'bg-gradient-to-br from-emerald-950/20 via-slate-900 to-slate-900 border-emerald-500/40 shadow-lg shadow-emerald-950/20'
                          : 'bg-slate-900/90 border-slate-800 hover:border-slate-700'
                      }`}
                    >
                      {/* Top Badges */}
                      <div className="space-y-2">
                        <div className="flex items-center justify-between gap-2 flex-wrap">
                          <div className="flex items-center space-x-2">
                            <span className="w-5 h-5 rounded-full bg-slate-800 text-slate-300 text-[11px] font-bold flex items-center justify-center">
                              #{item.rank || index + 1}
                            </span>
                            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-800 text-slate-300 border border-slate-700">
                              {item.category}
                            </span>
                            <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold border ${getAlignmentBadge(item.political_alignment)}`}>
                              {item.political_alignment}
                            </span>
                          </div>

                          {isInjected && (
                            <span className="px-2 py-0.5 text-[11px] font-bold rounded-md bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 flex items-center space-x-1">
                              <ShieldCheck className="w-3 h-3" />
                              <span>Diversity Injected</span>
                            </span>
                          )}
                        </div>

                        {/* Title & Snippet */}
                        <h3 className="text-base font-bold text-slate-100 hover:text-sky-400 transition leading-snug pt-1">
                          {item.title}
                        </h3>
                        <p className="text-xs text-slate-400 leading-relaxed line-clamp-3">
                          {item.snippet}
                        </p>

                        {/* Injection Explanation if applied */}
                        {isInjected && item.injected_reason && (
                          <div className="p-2 rounded-lg bg-emerald-950/40 border border-emerald-800/40 text-[11px] text-emerald-300/90 flex items-start space-x-2">
                            <Info className="w-3.5 h-3.5 flex-shrink-0 mt-0.5 text-emerald-400" />
                            <span>{item.injected_reason}</span>
                          </div>
                        )}
                      </div>

                      {/* Footer Actions & Scores */}
                      <div className="mt-4 pt-3 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400">
                        <div className="space-y-0.5">
                          <span className="text-[11px] font-medium text-slate-300">{item.source}</span>
                          <div className="text-[10px] text-slate-500 flex space-x-2">
                            <span>Hybrid: <strong className="text-sky-400 font-mono">{(item.score || 0).toFixed(2)}</strong></span>
                            {item.cf_score !== undefined && (
                              <span>(CF 70%: {item.cf_score.toFixed(2)} • CB 30%: {item.cb_score.toFixed(2)})</span>
                            )}
                          </div>
                        </div>

                        {/* Thumbs Up / Thumbs Down */}
                        <div className="flex items-center space-x-1.5 bg-slate-950/70 p-1 rounded-xl border border-slate-800">
                          <button
                            onClick={() => handleVote(item.article_id, 'like')}
                            title="Upvote (Thumbs Up)"
                            className={`p-1.5 rounded-lg transition flex items-center space-x-1 ${
                              vote === 'like'
                                ? 'bg-sky-500 text-white font-bold shadow-md shadow-sky-500/30'
                                : 'hover:bg-slate-800 text-slate-400 hover:text-slate-200'
                            }`}
                          >
                            <ThumbsUp className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={() => handleVote(item.article_id, 'dislike')}
                            title="Downvote (Thumbs Down)"
                            className={`p-1.5 rounded-lg transition flex items-center space-x-1 ${
                              vote === 'dislike'
                                ? 'bg-rose-600 text-white font-bold shadow-md shadow-rose-600/30'
                                : 'hover:bg-slate-800 text-slate-400 hover:text-slate-200'
                            }`}
                          >
                            <ThumbsDown className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>
                    </article>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* TAB 2: INFINITE SCROLL FEED */}
        {activeTab === 'explore' && (
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {articles.map((art) => {
                const vote = userVotes[art.article_id || art.id];

                return (
                  <article
                    key={art.article_id || art.id}
                    className="bg-slate-900 border border-slate-800 rounded-2xl p-4 flex flex-col justify-between hover:border-slate-700 transition"
                  >
                    <div className="space-y-2">
                      <div className="flex items-center justify-between gap-1 flex-wrap">
                        <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-slate-800 text-slate-300">
                          {art.category}
                        </span>
                        <span className={`px-2 py-0.5 rounded-full text-[11px] font-semibold border ${getAlignmentBadge(art.political_alignment)}`}>
                          {art.political_alignment}
                        </span>
                      </div>
                      <h4 className="text-sm font-bold text-slate-100 hover:text-sky-400 transition line-clamp-2">
                        {art.title}
                      </h4>
                      <p className="text-xs text-slate-400 line-clamp-3">
                        {art.snippet}
                      </p>
                    </div>

                    <div className="mt-4 pt-3 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400">
                      <span className="text-[11px] text-slate-400">{art.source}</span>
                      <div className="flex items-center space-x-1 bg-slate-950 p-1 rounded-lg border border-slate-800">
                        <button
                          onClick={() => handleVote(art.article_id || art.id, 'like')}
                          className={`p-1 rounded ${vote === 'like' ? 'bg-sky-500 text-white' : 'hover:bg-slate-800 text-slate-400'}`}
                        >
                          <ThumbsUp className="w-3 h-3" />
                        </button>
                        <button
                          onClick={() => handleVote(art.article_id || art.id, 'dislike')}
                          className={`p-1 rounded ${vote === 'dislike' ? 'bg-rose-600 text-white' : 'hover:bg-slate-800 text-slate-400'}`}
                        >
                          <ThumbsDown className="w-3 h-3" />
                        </button>
                      </div>
                    </div>
                  </article>
                );
              })}
            </div>

            {hasMore && (
              <div className="text-center py-6">
                <button
                  onClick={() => {
                    const nextPage = page + 1;
                    setPage(nextPage);
                    fetchArticles(nextPage, activeCategory, false);
                  }}
                  disabled={loadingMore}
                  className="px-6 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-white text-sm font-semibold transition border border-slate-700 disabled:opacity-50"
                >
                  {loadingMore ? 'Loading articles...' : 'Load More Articles (Infinite Scroll)'}
                </button>
              </div>
            )}
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800/80 bg-slate-900/50 py-4 text-center text-xs text-slate-500">
        NewsTailor • AI/ML Full-Stack Hybrid RecSys Assignment • Embed Square Solutions Pvt. Ltd.
      </footer>
    </div>
  );
}
