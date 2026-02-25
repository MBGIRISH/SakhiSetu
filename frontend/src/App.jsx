import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Landing from './pages/Landing'
import Schemes from './pages/Schemes'
import Eligibility from './pages/Eligibility'
import Chat from './pages/Chat'
import Simplify from './pages/Simplify'

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/schemes" element={<Schemes />} />
        <Route path="/eligibility" element={<Eligibility />} />
        <Route path="/chat" element={<Chat />} />
        <Route path="/simplify" element={<Simplify />} />
      </Routes>
    </Layout>
  )
}

export default App
