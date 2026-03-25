import { Routes, Route, Navigate } from 'react-router-dom'
import { DataProvider } from './hooks/useData'
import Explorar from './pages/Explorar'

function Nav() {
  return (
    <nav className="bg-white border-b border-gray-200 px-6 py-3 flex items-center sticky top-0 z-50">
      <span className="font-semibold text-gray-900 text-lg">Ecosistema Gipuzkoa</span>
    </nav>
  )
}

export default function App() {
  return (
    <DataProvider>
      <div className="min-h-screen bg-gray-50">
        <Nav />
        <Routes>
          <Route path="/explorar" element={<Explorar />} />
          <Route path="*" element={<Navigate to="/explorar" replace />} />
        </Routes>
      </div>
    </DataProvider>
  )
}
