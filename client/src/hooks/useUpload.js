import { useState, useCallback } from 'react';
import { uploadFile as uploadFileAPI } from '../utils/api';

export function useUpload() {
  const [isProcessing, setIsProcessing] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const upload = useCallback(async (file) => {
    if (!file || isProcessing) return;

    setIsProcessing(true);
    setError(null);
    setResult(null);

    try {
      const data = await uploadFileAPI(file);
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsProcessing(false);
    }
  }, [isProcessing]);

  const reset = useCallback(() => {
    setResult(null);
    setError(null);
  }, []);

  return { isProcessing, result, error, upload, reset };
}
