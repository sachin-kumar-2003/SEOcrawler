import { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import { FiSearch } from 'react-icons/fi';
import { AiOutlineLink, AiOutlineCloseCircle } from 'react-icons/ai';
import { HiDownload } from 'react-icons/hi';

function App() {
  const [url, setUrl] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [realTimeData, setRealTimeData] = useState({
    brokenLinks: [],
    workingLinks: [],
    totalVisited: 0,
    crawlStatus: ''
  });
  const wsRef = useRef(null);

  useEffect(() => {
    // Initialize WebSocket connection
    const connectWebSocket = () => {
      wsRef.current = new WebSocket('ws://127.0.0.1:8000/ws');
      
      wsRef.current.onopen = () => {
        console.log('WebSocket connected');
      };

      wsRef.current.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        switch (data.type) {
          case 'crawl_started':
            setRealTimeData(prev => ({
              ...prev,
              crawlStatus: data.message,
              brokenLinks: [],
              workingLinks: [],
              totalVisited: 0
            }));
            break;
            
          case 'broken_link':
            setRealTimeData(prev => ({
              ...prev,
              brokenLinks: [...prev.brokenLinks, data.url],
              totalVisited: data.total_visited
            }));
            break;
            
          case 'working_link':
            setRealTimeData(prev => ({
              ...prev,
              workingLinks: [...prev.workingLinks, data.url],
              totalVisited: data.total_visited
            }));
            break;
            
          case 'crawl_completed':
            setRealTimeData(prev => ({
              ...prev,
              crawlStatus: data.message
            }));
            break;
            
          default:
            console.log('Unknown message type:', data.type);
        }
      };

      wsRef.current.onclose = () => {
        console.log('WebSocket disconnected, attempting to reconnect...');
        setTimeout(connectWebSocket, 3000);
      };

      wsRef.current.onerror = (error) => {
        console.error('WebSocket error:', error);
      };
    };

    connectWebSocket();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const downloadLinks = (links, filename) => {
    const blob = new Blob([links.join('\n')], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleCrawl = async () => {
    if (!url) return;
    setLoading(true);
    setResult(null);
    
    // Reset real-time data
    setRealTimeData({
      brokenLinks: [],
      workingLinks: [],
      totalVisited: 0,
      crawlStatus: ''
    });

    try {
      const response = await axios.post('http://127.0.0.1:8000/crawl', { url });
      setResult(response.data);
    } catch (err) {
      console.error(err);
      alert('Something went wrong!');
    } finally {
      setLoading(false);
    }
  };

  const currentBrokenLinks = loading ? realTimeData.brokenLinks : (result?.result?.broken_links || []);
  const currentWorkingLinks = loading ? realTimeData.workingLinks : (result?.result?.correct_links || []);
  const currentTotalVisited = loading ? realTimeData.totalVisited : (result?.result?.total_visited || 0);

  return (
    <div className="min-h-screen flex flex-col items-center p-6 bg-gray-100 text-gray-800">
      <h1 className="text-4xl font-bold mb-2">SEO Link Auditor</h1>
      <p className="text-gray-600 mb-8 text-center max-w-xl">
        Instantly identify broken and valid links to optimize your site's SEO performance.
      </p>

      <div className="flex w-full max-w-xl bg-white border border-gray-300 rounded-md shadow-sm overflow-hidden">
        <input
          type="text"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="Enter URL..."
          className="flex-grow px-4 py-3 text-gray-800 focus:outline-none"
          disabled={loading}
        />
        <button
          onClick={handleCrawl}
          disabled={loading}
          className="bg-blue-500 hover:bg-blue-600 disabled:bg-blue-300 text-white px-6 transition-colors flex items-center justify-center"
        >
          <FiSearch className="mr-2" />
          {loading ? 'Crawling...' : 'Crawl'}
        </button>
      </div>

      {loading && (
        <div className="mt-6 text-center">
          <p className="font-medium text-blue-500 animate-pulse">🔍 {realTimeData.crawlStatus || 'Crawling... hang tight.'}</p>
          {realTimeData.totalVisited > 0 && (
            <p className="text-sm text-gray-600 mt-2">Pages visited: {realTimeData.totalVisited}</p>
          )}
        </div>
      )}

      {(loading || result) && (
        <div className="w-full max-w-5xl mt-12 p-8 rounded-lg bg-white border border-gray-300 shadow-md">
          <p className="mb-6 text-lg">
            <strong>Total pages visited:</strong> {currentTotalVisited}
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {/* 🔴 Broken Links */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <h2 className="text-xl font-semibold text-red-500 flex items-center">
                  <AiOutlineCloseCircle className="mr-2" />
                  Broken Links ({currentBrokenLinks.length})
                  {loading && <span className="ml-2 text-sm animate-pulse">📡 Live</span>}
                </h2>
                {currentBrokenLinks.length > 0 && (
                  <button
                    onClick={() => downloadLinks(currentBrokenLinks, 'broken_links.txt')}
                    className="p-2 hover:text-red-600 transition"
                    title="Download Broken Links"
                  >
                    <HiDownload className="text-xl" />
                  </button>
                )}
              </div>
              <div className="max-h-64 overflow-y-auto p-4 border border-red-200 bg-red-50 rounded-md shadow-sm">
                {currentBrokenLinks.length === 0 ? (
                  <p className="text-red-600 italic">
                    {loading ? 'No broken links found yet...' : 'No broken links detected.'}
                  </p>
                ) : (
                  <ul className="space-y-2 list-disc pl-5 text-red-600 text-sm">
                    {currentBrokenLinks.map((link, i) => (
                      <li key={i} className={loading && i === currentBrokenLinks.length - 1 ? 'animate-pulse bg-red-100 p-1 rounded' : ''}>
                        <a
                          href={link}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="hover:underline break-words"
                        >
                          {link}
                        </a>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>

            {/* ✅ Working Links */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <h2 className="text-xl font-semibold text-green-600 flex items-center">
                  <AiOutlineLink className="mr-2" />
                  Working Links ({currentWorkingLinks.length})
                  {loading && <span className="ml-2 text-sm animate-pulse">📡 Live</span>}
                </h2>
                {currentWorkingLinks.length > 0 && (
                  <button
                    onClick={() => downloadLinks(currentWorkingLinks, 'correct_links.txt')}
                    className="p-2 hover:text-green-600 transition"
                    title="Download Working Links"
                  >
                    <HiDownload className="text-xl" />
                  </button>
                )}
              </div>
              <div className="max-h-64 overflow-y-auto p-4 border border-green-200 bg-green-50 rounded-md shadow-sm">
                {currentWorkingLinks.length === 0 ? (
                  <p className="text-green-600 italic">
                    {loading ? 'No working links found yet...' : 'No valid links found.'}
                  </p>
                ) : (
                  <ul className="space-y-2 list-disc pl-5 text-green-600 text-sm">
                    {currentWorkingLinks.map((link, i) => (
                      <li key={i} className={loading && i === currentWorkingLinks.length - 1 ? 'animate-pulse bg-green-100 p-1 rounded' : ''}>
                        <a
                          href={link}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="hover:underline break-words"
                        >
                          {link}
                        </a>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;