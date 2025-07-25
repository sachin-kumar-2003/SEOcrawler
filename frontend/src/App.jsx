import { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import { FiSearch, FiX, FiGlobe, FiActivity } from 'react-icons/fi';
import { AiOutlineLink, AiOutlineCloseCircle } from 'react-icons/ai';
import { HiDownload, HiLightningBolt } from 'react-icons/hi';


const backendUrl = import.meta.env.VITE_APP_BACKEND_URL;
// const backendUrl = '127.0.0.1:8000'; 

const domain = import.meta.env.VITE_APP_WS_URL;
// const domain = '127.0.0.1:8000' 


function App() {
  const [url, setUrl] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [crawlController, setCrawlController] = useState(null);
  const [realTimeData, setRealTimeData] = useState({
    brokenLinks: [],
    workingLinks: [],
    totalVisited: 0,
    crawlStatus: ''
  });
  const wsRef = useRef(null);

  const connectWebSocket = () => {
    // Close any existing connection first
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.close();
    }
    wsRef.current = new WebSocket(`wss://${domain}/ws`);
    // wsRef.current = new WebSocket(`ws://${domain}/ws`);

    
    
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
          // Close WebSocket after crawl completes
          setTimeout(() => {
            if (wsRef.current) {
              wsRef.current.close();
            }
          }, 1000);
          break;
          
        default:
          console.log('Unknown message type:', data.type);
      }
    };

    wsRef.current.onclose = () => {
      console.log('WebSocket disconnected');
    };

    wsRef.current.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  };

  useEffect(() => {
    return () => {
      // Cleanup on component unmount
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

const stopCrawling = () => {
  if (crawlController) {
    crawlController.abort();
    setCrawlController(null);
  }

  if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
    wsRef.current.send(JSON.stringify({ type: "stop" }));
    wsRef.current.close();
  }

  setLoading(false);
  setRealTimeData(prev => ({
    ...prev,
    crawlStatus: "Crawling stopped by user"
  }));
};


  const handleCrawl = async () => {
    if (!url) return;
    
    // Close any existing WebSocket and start fresh
    if (wsRef.current) {
      wsRef.current.close();
    }
    
    // Connect WebSocket for this crawl session
    connectWebSocket();
    
    setLoading(true);
    setResult(null);
    
    // Create AbortController for this request
    const controller = new AbortController();
    setCrawlController(controller);
    
    // Reset real-time data
    setRealTimeData({
      brokenLinks: [],
      workingLinks: [],
      totalVisited: 0,
      crawlStatus: ''
    });

    try {
      const response = await axios.post(`https://${backendUrl}/crawl`, { url }, {
      // const response = await axios.post(`http://${backendUrl}/crawl`, { url }, {
        signal: controller.signal
      });
      setResult(response.data);
    } catch (err) {
      if (err.name === 'CanceledError' || err.code === 'ERR_CANCELED') {
        console.log('Crawl was cancelled by user');
      } else {
        console.error(err);
        alert('Something went wrong!');
      }
      // Close WebSocket on error
      if (wsRef.current) {
        wsRef.current.close();
      }
    } finally {
      setLoading(false);
      setCrawlController(null);
    }
  };

  const currentBrokenLinks = loading ? realTimeData.brokenLinks : (result?.result?.broken_links || []);
  const currentWorkingLinks = loading ? realTimeData.workingLinks : (result?.result?.correct_links || []);
  const currentTotalVisited = loading ? realTimeData.totalVisited : (result?.result?.total_visited || 0);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      {/* Animated background elements */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute -top-1/2 -right-1/2 w-full h-full bg-gradient-to-br from-purple-500/20 to-pink-500/20 rounded-full blur-3xl animate-pulse"></div>
        <div className="absolute -bottom-1/2 -left-1/2 w-full h-full bg-gradient-to-tr from-blue-500/20 to-cyan-500/20 rounded-full blur-3xl animate-pulse delay-1000"></div>
      </div>
      
      <div className="relative z-10 flex flex-col items-center p-6 text-white">
        {/* Header Section */}
        <div className="text-center mb-12 mt-8">
          <div className="flex items-center justify-center mb-4">
            <div className="p-4 bg-gradient-to-r from-purple-500 to-pink-500 rounded-2xl shadow-2xl">
              <FiGlobe className="text-4xl text-white" />
            </div>
          </div>
          <h1 className="text-6xl font-bold mb-4 bg-gradient-to-r from-purple-400 via-pink-400 to-cyan-400 bg-clip-text text-transparent">
            SEO Link Auditor
          </h1>
          <p className="text-gray-300 text-xl max-w-2xl leading-relaxed">
            Discover and analyze your website's link structure with real-time monitoring. 
            Identify broken links and optimize your site's SEO performance instantly.
          </p>
          
          {/* Feature badges */}
          <div className="flex flex-wrap justify-center gap-3 mt-6">
            <div className="flex items-center bg-white/10 backdrop-blur-lg rounded-full px-4 py-2 border border-white/20">
              <HiLightningBolt className="text-yellow-400 mr-2" />
              <span className="text-sm">Real-time Analysis</span>
            </div>
            <div className="flex items-center bg-white/10 backdrop-blur-lg rounded-full px-4 py-2 border border-white/20">
              <FiActivity className="text-green-400 mr-2" />
              <span className="text-sm">Live Updates</span>
            </div>
            <div className="flex items-center bg-white/10 backdrop-blur-lg rounded-full px-4 py-2 border border-white/20">
              <HiDownload className="text-blue-400 mr-2" />
              <span className="text-sm">Export Results</span>
            </div>
          </div>
        </div>

        {/* Search Section */}
        <div className="w-full max-w-2xl mb-8">
          <div className="relative">
            <div className="absolute inset-0 bg-gradient-to-r from-purple-500 to-pink-500 rounded-2xl blur opacity-75 group-hover:opacity-100 transition duration-1000"></div>
            <div className="relative flex bg-white/10 backdrop-blur-lg border border-white/20 rounded-2xl shadow-2xl overflow-hidden">
              <div className="flex-grow">
                <input
                  type="text"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder="Enter your website URL..."
                  className="w-full px-6 py-4 text-white bg-transparent placeholder-gray-300 focus:outline-none text-lg"
                  disabled={loading}
                />
              </div>
              <div className="flex">
                <button
                  onClick={handleCrawl}
                  disabled={loading}
                  className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 disabled:from-gray-600 disabled:to-gray-700 text-white px-8 py-4 transition-all duration-300 flex items-center justify-center font-semibold text-lg group"
                >
                  <FiSearch className="mr-2 group-hover:rotate-90 transition-transform duration-300" />
                  {loading ? 'Analyzing...' : 'Start Audit'}
                </button>
                
                {loading && (
                  <button
                    onClick={stopCrawling}
                    className="bg-gradient-to-r from-red-600 to-pink-600 hover:from-red-700 hover:to-pink-700 text-white px-6 transition-all duration-300 flex items-center justify-center border-l border-white/20 group"
                    title="Stop Analysis"
                  >
                    <FiX className="text-xl group-hover:rotate-90 transition-transform duration-300" />
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Status Section */}
        {loading && (
          <div className="text-center mb-8">
            <div className="bg-white/10 backdrop-blur-lg rounded-2xl px-8 py-6 border border-white/20 shadow-2xl">
               <div className="flex items-center justify-center mb-4">
                <div className="animate-spin rounded-full h-8 w-8 border-4 border-purple-400 border-t-transparent mr-3"></div>
                <p className="text-xl font-semibold text-purple-300">
                  {realTimeData.crawlStatus || 'Scanning your website...'}
                </p>
              </div> 
              {realTimeData.totalVisited > 0 && (
                <div className="flex items-center justify-center space-x-8 text-sm">
                  {/* <div className="flex items-center">
                    <div className="w-3 h-3 bg-purple-400 rounded-full mr-2 animate-pulse"></div>
                    <span className="text-gray-300">Pages Visited: <span className="text-white font-semibold">{realTimeData.totalVisited}</span></span>
                  </div> */}
                  <div className="flex items-center">
                    <div className="w-3 h-3 bg-green-400 rounded-full mr-2 animate-pulse"></div>
                    <span className="text-gray-300">Working: <span className="text-green-400 font-semibold">{currentWorkingLinks.length}</span></span>
                  </div>
                  <div className="flex items-center">
                    <div className="w-3 h-3 bg-red-400 rounded-full mr-2 animate-pulse"></div>
                    <span className="text-gray-300">Broken: <span className="text-red-400 font-semibold">{currentBrokenLinks.length}</span></span>
                  </div>
                </div>
              )}
              <p className="text-sm text-gray-400 mt-3">Click the ✕ button to stop the analysis</p>
            </div>
          </div>
        )}

        {/* Results Section */}
        {(loading || result) && (
          <div className="w-full max-w-7xl">
            <div className="bg-white/10 backdrop-blur-lg rounded-3xl p-8 border border-white/20 shadow-2xl">
              {/* Summary Stats */}
              <div className="mb-8">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  {/* <div className="bg-gradient-to-br from-purple-500/20 to-pink-500/20 rounded-2xl p-6 border border-purple-500/30">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-purple-300 text-sm font-medium">Pages Scanned</p>
                        <p className="text-3xl font-bold text-white mt-1">{currentTotalVisited}</p>
                      </div>
                      <FiGlobe className="text-4xl text-purple-400" />
                    </div>
                  </div> */}
                  
                  <div className="bg-gradient-to-br from-green-500/20 to-emerald-500/20 rounded-2xl p-6 border border-green-500/30">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-green-300 text-sm font-medium">Working Links</p>
                        <p className="text-3xl font-bold text-white mt-1">{currentWorkingLinks.length}</p>
                      </div>
                      <AiOutlineLink className="text-4xl text-green-400" />
                    </div>
                  </div>
                  
                  <div className="bg-gradient-to-br from-red-500/20 to-pink-500/20 rounded-2xl p-6 border border-red-500/30">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-red-300 text-sm font-medium">Broken Links</p>
                        <p className="text-3xl font-bold text-white mt-1">{currentBrokenLinks.length}</p>
                      </div>
                      <AiOutlineCloseCircle className="text-4xl text-red-400" />
                    </div>
                  </div>
                </div>
              </div>

              {/* Links Display */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                {/* Broken Links */}
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <h2 className="text-2xl font-bold text-red-400 flex items-center">
                      <AiOutlineCloseCircle className="mr-3" />
                      Broken Links ({currentBrokenLinks.length})
                      {loading && <span className="ml-3 text-sm animate-pulse bg-red-500/20 px-3 py-1 rounded-full border border-red-500/30">🔴 Live</span>}
                    </h2>
                    {currentBrokenLinks.length > 0 && (
                      <button
                        onClick={() => downloadLinks(currentBrokenLinks, 'broken_links.txt')}
                        className="p-3 bg-red-500/20 hover:bg-red-500/30 border border-red-500/30 rounded-xl transition-all duration-300 group"
                        title="Download Broken Links"
                      >
                        <HiDownload className="text-xl text-red-400 group-hover:scale-110 transition-transform duration-300" />
                      </button>
                    )}
                  </div>
                  
                  <div className="bg-red-500/10 backdrop-blur-lg rounded-2xl border border-red-500/20 max-h-96 overflow-hidden">
                    <div className="max-h-96 overflow-y-auto p-6">
                      {currentBrokenLinks.length === 0 ? (
                        <div className="text-center py-8">
                          <AiOutlineCloseCircle className="text-6xl text-red-400/50 mx-auto mb-4" />
                          <p className="text-red-300 text-lg">
                            {loading ? 'No broken links found yet...' : 'No broken links detected! 🎉'}
                          </p>
                        </div>
                      ) : (
                        <ul className="space-y-3">
                          {currentBrokenLinks.map((link, i) => (
                            <li key={i} className={`p-4 rounded-xl border border-red-500/20 transition-all duration-300 ${loading && i === currentBrokenLinks.length - 1 ? 'bg-red-500/20 animate-pulse scale-105' : 'bg-red-500/10 hover:bg-red-500/20'}`}>
                              <a
                                href={link}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-red-300 hover:text-red-200 break-all transition-colors duration-300 text-sm"
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

                {/* Working Links */}
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <h2 className="text-2xl font-bold text-green-400 flex items-center">
                      <AiOutlineLink className="mr-3" />
                      Working Links ({currentWorkingLinks.length})
                      {loading && <span className="ml-3 text-sm animate-pulse bg-green-500/20 px-3 py-1 rounded-full border border-green-500/30">🟢 Live</span>}
                    </h2>
                    {currentWorkingLinks.length > 0 && (
                      <button
                        onClick={() => downloadLinks(currentWorkingLinks, 'working_links.txt')}
                        className="p-3 bg-green-500/20 hover:bg-green-500/30 border border-green-500/30 rounded-xl transition-all duration-300 group"
                        title="Download Working Links"
                      >
                        <HiDownload className="text-xl text-green-400 group-hover:scale-110 transition-transform duration-300" />
                      </button>
                    )}
                  </div>
                  
                  <div className="bg-green-500/10 backdrop-blur-lg rounded-2xl border border-green-500/20 max-h-96 overflow-hidden">
                    <div className="max-h-96 overflow-y-auto p-6">
                      {currentWorkingLinks.length === 0 ? (
                        <div className="text-center py-8">
                          <AiOutlineLink className="text-6xl text-green-400/50 mx-auto mb-4" />
                          <p className="text-green-300 text-lg">
                            {loading ? 'No working links found yet...' : 'No valid links found.'}
                          </p>
                        </div>
                      ) : (
                        <ul className="space-y-3">
                          {currentWorkingLinks.map((link, i) => (
                            <li key={i} className={`p-4 rounded-xl border border-green-500/20 transition-all duration-300 ${loading && i === currentWorkingLinks.length - 1 ? 'bg-green-500/20 animate-pulse scale-105' : 'bg-green-500/10 hover:bg-green-500/20'}`}>
                              <a
                                href={link}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-green-300 hover:text-green-200 break-all transition-colors duration-300 text-sm"
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
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;