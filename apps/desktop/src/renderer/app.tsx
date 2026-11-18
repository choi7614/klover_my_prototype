import { HashRouter, Navigate, Route, Routes } from 'react-router-dom';
import { OnboardingStartPage } from './features/onboarding/onboarding-start-page';

export function App() {
  return (
    <HashRouter>
      <Routes>
        <Route path="/onboarding/1" element={<OnboardingStartPage />} />
        <Route path="*" element={<Navigate to="/onboarding/1" replace />} />
      </Routes>
    </HashRouter>
  );
}
