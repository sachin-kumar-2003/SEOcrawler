import { useState } from 'react';
import axios from 'axios';
import { FiSearch } from 'react-icons/fi';
import { AiOutlineLink, AiOutlineCloseCircle } from 'react-icons/ai';
import { HiDownload } from 'react-icons/hi';

function App() {
  const [url, setUrl] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

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
        />
        <button
          onClick={handleCrawl}
          className="bg-blue-500 hover:bg-blue-600 text-white px-6 transition-colors flex items-center justify-center"
        >
          <FiSearch className="mr-2" />
          Crawl
        </button>
      </div>

      {loading && (
        <p className="mt-10 font-medium text-blue-500 animate-pulse">🔍 Crawling... hang tight.</p>
      )}

      {result && (
        <div className="w-full max-w-5xl mt-12 p-8 rounded-lg bg-white border border-gray-300 shadow-md">
          <p className="mb-6 text-lg">
            <strong>Total pages visited:</strong> {result.result.total_visited}
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {/* 🔴 Broken Links */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <h2 className="text-xl font-semibold text-red-500 flex items-center">
                  <AiOutlineCloseCircle className="mr-2" />
                  Broken Links
                </h2>
                {result.result.broken_links.length > 0 && (
                  <button
                    onClick={() => downloadLinks(result.result.broken_links, 'broken_links.txt')}
                    className="p-2 hover:text-red-600 transition"
                    title="Download Broken Links"
                  >
                    <HiDownload className="text-xl" />
                  </button>
                )}
              </div>
              <div className="max-h-64 overflow-y-auto p-4 border border-red-200 bg-red-50 rounded-md shadow-sm">
                {result.result.broken_links.length === 0 ? (
                  <p className="text-red-600 italic">No broken links detected.</p>
                ) : (
                  <ul className="space-y-2 list-disc pl-5 text-red-600 text-sm">
                    {result.result.broken_links.map((link, i) => (
                      <li key={i}>
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
                  Working Links
                </h2>
                {result.result.correct_links.length > 0 && (
                  <button
                    onClick={() => downloadLinks(result.result.correct_links, 'correct_links.txt')}
                    className="p-2 hover:text-green-600 transition"
                    title="Download Working Links"
                  >
                    <HiDownload className="text-xl" />
                  </button>
                )}
              </div>
              <div className="max-h-64 overflow-y-auto p-4 border border-green-200 bg-green-50 rounded-md shadow-sm">
                {result.result.correct_links.length === 0 ? (
                  <p className="text-green-600 italic">No valid links found.</p>
                ) : (
                  <ul className="space-y-2 list-disc pl-5 text-green-600 text-sm">
                    {result.result.correct_links.map((link, i) => (
                      <li key={i}>
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
