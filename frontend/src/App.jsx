import { useState } from 'react'
import axios from 'axios'
import './App.css'

function App() {
  const [url, setUrl] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleCrawl = async () => {
    if (!url) return;
    setLoading(true);
    setResult(null);

    try {
      const response = await axios.post('http://127.0.0.1:8000/crawl', {
      url: url  
    });
    console.log(response)
      setResult(response.data);
    } catch (error) {
      console.error(error);
      alert('Something went wrong!');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen p-8 bg-gray-100 flex flex-col items-center">
      <h1 className="text-3xl mb-4 font-bold">SEO Broken Link Checker</h1>
      <div className="mb-4 flex gap-2">
        <input
          className="p-2 border border-gray-400 rounded w-96"
          type="text"
          placeholder="Enter URL (e.g., https://example.com)"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
        />
        <button
          className="bg-blue-500 text-white px-4 py-2 rounded"
          onClick={handleCrawl}
        >
          Start Crawl
        </button>
      </div>

      {loading && <p className="text-lg">Crawling... Please wait.</p>}

      {result && (
        <div className="w-full max-w-3xl mt-8 bg-white p-4 rounded shadow">
          <h2 className="text-xl font-bold mb-2">Result</h2>
          <p><strong>Total visited:</strong> {result.data.result.total_visited}</p>

          <h3 className="text-lg mt-4 font-semibold">Broken Links ({result.data.result.broken_links.length}):</h3>
          <ul className="list-disc list-inside">
            {result.broken_links.map((link, i) => (
              <li key={i}>
                <a href={link} target="_blank" rel="noopener noreferrer" className="text-red-600 underline">
                  {link}
                </a>
              </li>
            ))}
          </ul>

          <h3 className="text-lg mt-4 font-semibold">Correct Links ({result.data.result.correct_links.length}):</h3>
          <ul className="list-disc list-inside">
            {result.correct_links.map((link, i) => (
              <li key={i}>
                <a href={link} target="_blank" rel="noopener noreferrer" className="text-green-700 underline">
                  {link}
                </a>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export default App;
