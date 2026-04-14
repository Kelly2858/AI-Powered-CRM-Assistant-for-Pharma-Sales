import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import axios from 'axios';

const API_URL = 'http://localhost:8000/api';

export const fetchHCPs = createAsyncThunk(
  'hcps/fetchAll',
  async (search = '', { rejectWithValue }) => {
    try {
      const url = search ? `${API_URL}/hcps?search=${encodeURIComponent(search)}` : `${API_URL}/hcps`;
      const response = await axios.get(url);
      return response.data;
    } catch (error) {
      return rejectWithValue(error.response?.data?.detail || 'Failed to fetch HCPs');
    }
  }
);

const hcpSlice = createSlice({
  name: 'hcps',
  initialState: {
    list: [],
    loading: false,
    error: null,
  },
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(fetchHCPs.pending, (state) => { state.loading = true; })
      .addCase(fetchHCPs.fulfilled, (state, action) => {
        state.loading = false;
        state.list = action.payload;
      })
      .addCase(fetchHCPs.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      });
  },
});

export default hcpSlice.reducer;
