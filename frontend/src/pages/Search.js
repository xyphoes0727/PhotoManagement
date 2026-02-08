import React, { useState } from 'react';
import { Search as SearchIcon, Loader, Image, AlertCircle } from 'lucide-react';
import { queryPhotos } from '../services/api';
import './Search.css';

const Search = () => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [hasSearched, setHasSearched] = useState(false);

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setError(null);
    setHasSearched(true);

    try {
      // API search
      const apiResults = await queryPhotos(query.trim());
      
      // Map API results to display format
      let matchedPhotos = [];
      if (Array.isArray(apiResults) && apiResults.length > 0) {
        matchedPhotos = apiResults.map(result => {
          const id = result.id || result;
          return {
            id,
            score: result.score,
            name: `Photo ${id}`,
            caption: '',
            preview: null
          };
        });
      }
      
      setResults(matchedPhotos);
    } catch (err) {
      setError(err.message);
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  const searchSuggestions = [
    'sunset at beach',
    'family gathering',
    'birthday party',
    'mountain hiking',
    'city skyline',
    'food and cooking',
  ];

  return (
    <div className="search-page">
      <div className="search-header">
        <h2>Search Your Photos</h2>
        <p>Use natural language to find photos in your collection</p>
      </div>

      <form onSubmit={handleSearch} className="search-form">
        <div className="search-input-wrapper">
          <SearchIcon size={20} className="search-input-icon" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Describe what you're looking for..."
            className="search-input"
          />
          <button 
            type="submit" 
            className="search-btn"
            disabled={loading || !query.trim()}
          >
            {loading ? (
              <Loader size={20} className="spin" />
            ) : (
              'Search'
            )}
          </button>
        </div>
      </form>

      {!hasSearched && (
        <div className="search-suggestions">
          <h3>Try searching for:</h3>
          <div className="suggestion-tags">
            {searchSuggestions.map((suggestion, index) => (
              <button
                key={index}
                className="suggestion-tag"
                onClick={() => setQuery(suggestion)}
              >
                {suggestion}
              </button>
            ))}
          </div>
        </div>
      )}

      {error && (
        <div className="search-error">
          <AlertCircle size={20} />
          <span>{error}</span>
        </div>
      )}

      {hasSearched && !loading && !error && (
        <div className="search-results">
          <div className="results-header">
            <h3>
              {results.length > 0 
                ? `Found ${results.length} matching photo${results.length !== 1 ? 's' : ''}`
                : 'No photos found'
              }
            </h3>
            {query && <span className="search-query">for "{query}"</span>}
          </div>

          {results.length > 0 ? (
            <div className="results-grid">
              {results.map((result, index) => (
                <div key={result.id || index} className="result-card">
                  <div className="result-preview">
                    {result.preview ? (
                      <img src={result.preview} alt={result.name || 'Photo'} className="result-img" />
                    ) : (
                      <Image size={48} />
                    )}
                  </div>
                  <div className="result-info">
                    <span className="result-id">{result.name || result.id || result}</span>
                    {result.caption && (
                      <span className="result-caption">{result.caption}</span>
                    )}
                    {result.score && (
                      <span className="result-score">
                        Match: {(result.score * 100).toFixed(1)}%
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="no-results">
              <Image size={64} className="no-results-icon" />
              <h3>No matching photos</h3>
              <p>Try a different search term or upload more photos</p>
            </div>
          )}
        </div>
      )}

      <div className="search-tips">
        <h3>🔍 Search Tips</h3>
        <ul>
          <li>Use descriptive phrases like "red car in parking lot"</li>
          <li>Describe activities: "people playing soccer"</li>
          <li>Mention locations: "photos from the mountains"</li>
          <li>Include objects: "cat sleeping on couch"</li>
        </ul>
      </div>
    </div>
  );
};

export default Search;
