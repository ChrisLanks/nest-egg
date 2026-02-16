/**
 * CSV Import Modal for uploading and importing transaction CSV files
 * Supports Mint.com format and custom column mapping
 */

import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  ModalCloseButton,
  Button,
  VStack,
  HStack,
  Text,
  Input,
  FormControl,
  FormLabel,
  Select,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Box,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
  useToast,
  Progress,
  Badge,
  Code,
} from '@chakra-ui/react';
import { useState, useRef } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import api from '../services/api';

interface CSVImportModalProps {
  isOpen: boolean;
  onClose: () => void;
}

interface PreviewData {
  detected_columns: string[];
  detected_mapping: Record<string, string>;
  sample_rows: Record<string, any>[];
  total_rows: number;
}

interface ImportResult {
  imported: number;
  skipped: number;
  errors: number;
  error_details?: Array<{ row: number; error: string }>;
}

export const CSVImportModal: React.FC<CSVImportModalProps> = ({ isOpen, onClose }) => {
  const toast = useToast();
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [file, setFile] = useState<File | null>(null);
  const [selectedAccountId, setSelectedAccountId] = useState<string>('');
  const [step, setStep] = useState<'upload' | 'mapping' | 'preview' | 'importing' | 'complete'>('upload');
  const [previewData, setPreviewData] = useState<PreviewData | null>(null);
  const [columnMapping, setColumnMapping] = useState<Record<string, string>>({});
  const [importResult, setImportResult] = useState<ImportResult | null>(null);
  const [skipDuplicates, setSkipDuplicates] = useState(true);

  // Fetch accounts for account selector
  const { data: accounts } = useQuery({
    queryKey: ['accounts'],
    queryFn: async () => {
      const response = await api.get('/accounts/');
      return response.data;
    },
    enabled: isOpen,
  });

  // Reset modal state when closed
  const handleClose = () => {
    setFile(null);
    setSelectedAccountId('');
    setStep('upload');
    setPreviewData(null);
    setColumnMapping({});
    setImportResult(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
    onClose();
  };

  const handleDownloadTemplate = () => {
    // Create CSV template with all supported columns and example data
    const template = [
      ['Date', 'Amount', 'Description', 'Merchant', 'Category', 'Notes', 'Account', 'Labels'],
      ['2024-01-15', '-45.67', 'Coffee shop purchase', 'Starbucks', 'Dining', 'Morning coffee', 'Credit Card', 'Business'],
      ['2024-01-16', '-123.45', 'Grocery shopping', 'Whole Foods', 'Groceries', 'Weekly groceries', 'Checking', ''],
      ['2024-01-17', '2500.00', 'Paycheck deposit', 'Employer Inc', 'Income', 'Salary', 'Checking', 'Income'],
      ['2024-01-18', '-89.99', 'Internet service', 'Comcast', 'Utilities', 'Monthly bill', 'Checking', 'Bills'],
      ['2024-01-19', '-35.20', 'Gas station', 'Shell', 'Transportation', 'Fuel', 'Credit Card', ''],
    ].map(row => row.join(',')).join('\n');

    const blob = new Blob([template], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', 'nest-egg-import-template.csv');
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);

    toast({
      title: 'Template downloaded',
      description: 'Use this template as a guide for formatting your CSV file',
      status: 'success',
      duration: 3000,
    });
  };

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = event.target.files?.[0];
    if (selectedFile) {
      if (!selectedFile.name.toLowerCase().endsWith('.csv')) {
        toast({
          title: 'Invalid file type',
          description: 'Please select a CSV file (.csv)',
          status: 'error',
          duration: 5000,
        });
        return;
      }
      setFile(selectedFile);
    }
  };

  // Preview mutation
  const previewMutation = useMutation({
    mutationFn: async () => {
      if (!file) throw new Error('No file selected');

      const formData = new FormData();
      formData.append('file', file);

      const response = await api.post('/csv-import/preview', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      return response.data;
    },
    onSuccess: (data: PreviewData) => {
      setPreviewData(data);
      setColumnMapping(data.detected_mapping || {});
      setStep('mapping');
    },
    onError: (error: any) => {
      toast({
        title: 'Preview failed',
        description: error?.response?.data?.detail || 'Failed to preview CSV file',
        status: 'error',
        duration: 5000,
      });
    },
  });

  // Import mutation
  const importMutation = useMutation({
    mutationFn: async () => {
      if (!file || !selectedAccountId) throw new Error('Missing file or account');

      const formData = new FormData();
      formData.append('file', file);

      const params = new URLSearchParams({
        account_id: selectedAccountId,
        skip_duplicates: String(skipDuplicates),
      });

      // Add column mapping as JSON if customized
      const mappingJson = JSON.stringify(columnMapping);

      const response = await api.post(
        `/csv-import/import?${params.toString()}`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
          params: {
            column_mapping: mappingJson !== '{}' ? mappingJson : undefined,
          },
        }
      );
      return response.data;
    },
    onSuccess: (data: ImportResult) => {
      setImportResult(data);
      setStep('complete');
      queryClient.invalidateQueries({ queryKey: ['transactions'] });
      queryClient.invalidateQueries({ queryKey: ['all-transactions-infinite'] });
      toast({
        title: 'Import successful',
        description: `Imported ${data.imported} transactions, skipped ${data.skipped}`,
        status: 'success',
        duration: 5000,
      });
    },
    onError: (error: any) => {
      toast({
        title: 'Import failed',
        description: error?.response?.data?.detail || 'Failed to import transactions',
        status: 'error',
        duration: 5000,
      });
      setStep('mapping');
    },
  });

  const handleNext = () => {
    if (step === 'upload') {
      if (!file) {
        toast({
          title: 'No file selected',
          description: 'Please select a CSV file to upload',
          status: 'warning',
          duration: 3000,
        });
        return;
      }
      if (!selectedAccountId) {
        toast({
          title: 'No account selected',
          description: 'Please select an account to import into',
          status: 'warning',
          duration: 3000,
        });
        return;
      }
      previewMutation.mutate();
    } else if (step === 'mapping') {
      // Validate required mappings
      if (!columnMapping.date || !columnMapping.amount) {
        toast({
          title: 'Missing required columns',
          description: 'Date and Amount columns are required',
          status: 'error',
          duration: 5000,
        });
        return;
      }
      setStep('preview');
    } else if (step === 'preview') {
      setStep('importing');
      importMutation.mutate();
    }
  };

  const handleBack = () => {
    if (step === 'mapping') {
      setStep('upload');
    } else if (step === 'preview') {
      setStep('mapping');
    }
  };

  const requiredFields = ['date', 'amount'];
  const optionalFields = ['description', 'merchant', 'category'];

  return (
    <Modal isOpen={isOpen} onClose={handleClose} size="4xl" scrollBehavior="inside">
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>
          Import Transactions from CSV
          <Text fontSize="sm" fontWeight="normal" color="gray.600" mt={1}>
            {step === 'upload' && 'Step 1: Upload your CSV file'}
            {step === 'mapping' && 'Step 2: Map columns'}
            {step === 'preview' && 'Step 3: Preview import'}
            {step === 'importing' && 'Importing...'}
            {step === 'complete' && 'Import Complete'}
          </Text>
        </ModalHeader>
        <ModalCloseButton />

        <ModalBody>
          {/* Step 1: Upload */}
          {step === 'upload' && (
            <VStack spacing={6} align="stretch">
              <Alert status="info">
                <AlertIcon />
                <Box flex={1}>
                  <AlertTitle>Supported Formats</AlertTitle>
                  <AlertDescription>
                    We support Mint.com export format and most standard CSV files with Date, Amount,
                    and Description columns.
                  </AlertDescription>
                </Box>
                <Button
                  size="sm"
                  variant="outline"
                  colorScheme="blue"
                  onClick={handleDownloadTemplate}
                  ml={4}
                >
                  Download Template
                </Button>
              </Alert>

              <FormControl isRequired>
                <FormLabel>Select Account</FormLabel>
                <Select
                  placeholder="Choose account to import into..."
                  value={selectedAccountId}
                  onChange={(e) => setSelectedAccountId(e.target.value)}
                >
                  {accounts?.map((account: any) => (
                    <option key={account.id} value={account.id}>
                      {account.name} ({account.institution_name || 'Manual'})
                    </option>
                  ))}
                </Select>
              </FormControl>

              <FormControl isRequired>
                <FormLabel>CSV File</FormLabel>
                <Input
                  type="file"
                  accept=".csv"
                  ref={fileInputRef}
                  onChange={handleFileSelect}
                  pt={1}
                />
                {file && (
                  <Text fontSize="sm" color="gray.600" mt={2}>
                    Selected: {file.name} ({(file.size / 1024).toFixed(1)} KB)
                  </Text>
                )}
              </FormControl>

              <Box bg="gray.50" p={4} borderRadius="md">
                <Text fontSize="sm" fontWeight="semibold" mb={2}>
                  💡 Tips for best results:
                </Text>
                <VStack align="stretch" spacing={1}>
                  <Text fontSize="sm">• Download our template above to see the recommended format</Text>
                  <Text fontSize="sm">• Ensure your CSV has headers in the first row</Text>
                  <Text fontSize="sm">• Date format: YYYY-MM-DD or MM/DD/YYYY</Text>
                  <Text fontSize="sm">• Amount: Negative for expenses, positive for income</Text>
                  <Text fontSize="sm">
                    • Required columns: <strong>Date</strong> and <strong>Amount</strong>
                  </Text>
                  <Text fontSize="sm">
                    • Optional columns: Description, Merchant, Category, Notes, Account, Labels
                  </Text>
                  <Text fontSize="sm">• Maximum file size: 10 MB</Text>
                </VStack>
              </Box>
            </VStack>
          )}

          {/* Step 2: Column Mapping */}
          {step === 'mapping' && previewData && (
            <VStack spacing={6} align="stretch">
              <Alert status="info">
                <AlertIcon />
                <Box>
                  <AlertTitle>Map Your Columns</AlertTitle>
                  <AlertDescription>
                    We detected {previewData.detected_columns.length} columns and{' '}
                    {previewData.total_rows} rows. Map them to our fields below.
                  </AlertDescription>
                </Box>
              </Alert>

              <FormControl isRequired>
                <FormLabel>Date Column</FormLabel>
                <Select
                  value={columnMapping.date || ''}
                  onChange={(e) => setColumnMapping({ ...columnMapping, date: e.target.value })}
                >
                  <option value="">-- Select Column --</option>
                  {previewData.detected_columns.map((col) => (
                    <option key={col} value={col}>
                      {col}
                    </option>
                  ))}
                </Select>
              </FormControl>

              <FormControl isRequired>
                <FormLabel>Amount Column</FormLabel>
                <Select
                  value={columnMapping.amount || ''}
                  onChange={(e) => setColumnMapping({ ...columnMapping, amount: e.target.value })}
                >
                  <option value="">-- Select Column --</option>
                  {previewData.detected_columns.map((col) => (
                    <option key={col} value={col}>
                      {col}
                    </option>
                  ))}
                </Select>
              </FormControl>

              <FormControl>
                <FormLabel>Description Column (Optional)</FormLabel>
                <Select
                  value={columnMapping.description || ''}
                  onChange={(e) =>
                    setColumnMapping({ ...columnMapping, description: e.target.value })
                  }
                >
                  <option value="">-- Select Column --</option>
                  {previewData.detected_columns.map((col) => (
                    <option key={col} value={col}>
                      {col}
                    </option>
                  ))}
                </Select>
              </FormControl>

              <FormControl>
                <FormLabel>Merchant Column (Optional)</FormLabel>
                <Select
                  value={columnMapping.merchant || ''}
                  onChange={(e) => setColumnMapping({ ...columnMapping, merchant: e.target.value })}
                >
                  <option value="">-- Select Column --</option>
                  {previewData.detected_columns.map((col) => (
                    <option key={col} value={col}>
                      {col}
                    </option>
                  ))}
                </Select>
              </FormControl>

              <Box>
                <Text fontWeight="semibold" mb={2}>
                  Sample Data Preview
                </Text>
                <Box overflowX="auto" maxH="200px" overflowY="auto" borderWidth={1} borderRadius="md">
                  <Table size="sm" variant="simple">
                    <Thead bg="gray.50" position="sticky" top={0}>
                      <Tr>
                        {previewData.detected_columns.slice(0, 5).map((col) => (
                          <Th key={col}>{col}</Th>
                        ))}
                      </Tr>
                    </Thead>
                    <Tbody>
                      {previewData.sample_rows.slice(0, 5).map((row, idx) => (
                        <Tr key={idx}>
                          {previewData.detected_columns.slice(0, 5).map((col) => (
                            <Td key={col} fontSize="sm">
                              {String(row[col] || '')}
                            </Td>
                          ))}
                        </Tr>
                      ))}
                    </Tbody>
                  </Table>
                </Box>
              </Box>
            </VStack>
          )}

          {/* Step 3: Preview */}
          {step === 'preview' && previewData && (
            <VStack spacing={6} align="stretch">
              <Alert status="success">
                <AlertIcon />
                <Box>
                  <AlertTitle>Ready to Import</AlertTitle>
                  <AlertDescription>
                    {previewData.total_rows} transactions will be imported into the selected account.
                  </AlertDescription>
                </Box>
              </Alert>

              <Box>
                <Text fontWeight="semibold" mb={2}>
                  Column Mapping Summary
                </Text>
                <VStack align="stretch" spacing={2}>
                  {Object.entries(columnMapping).map(([field, column]) => (
                    <HStack key={field} justify="space-between">
                      <Badge colorScheme="blue">{field}</Badge>
                      <Code fontSize="sm">{column}</Code>
                    </HStack>
                  ))}
                </VStack>
              </Box>

              <FormControl>
                <HStack>
                  <input
                    type="checkbox"
                    checked={skipDuplicates}
                    onChange={(e) => setSkipDuplicates(e.target.checked)}
                  />
                  <FormLabel mb={0}>Skip duplicate transactions</FormLabel>
                </HStack>
                <Text fontSize="sm" color="gray.600" ml={6}>
                  Transactions with matching date, amount, and merchant will be skipped
                </Text>
              </FormControl>
            </VStack>
          )}

          {/* Step 4: Importing */}
          {step === 'importing' && (
            <VStack spacing={6} align="stretch">
              <Alert status="info">
                <AlertIcon />
                <Box>
                  <AlertTitle>Importing Transactions</AlertTitle>
                  <AlertDescription>Please wait while we process your file...</AlertDescription>
                </Box>
              </Alert>
              <Progress size="lg" isIndeterminate colorScheme="blue" />
            </VStack>
          )}

          {/* Step 5: Complete */}
          {step === 'complete' && importResult && (
            <VStack spacing={6} align="stretch">
              <Alert status={importResult.errors > 0 ? 'warning' : 'success'}>
                <AlertIcon />
                <Box>
                  <AlertTitle>Import Complete</AlertTitle>
                  <AlertDescription>
                    Successfully imported {importResult.imported} transactions
                    {importResult.skipped > 0 && `, skipped ${importResult.skipped} duplicates`}
                    {importResult.errors > 0 && `, ${importResult.errors} errors`}
                  </AlertDescription>
                </Box>
              </Alert>

              <HStack spacing={8} justify="center" py={4}>
                <Box textAlign="center">
                  <Text fontSize="3xl" fontWeight="bold" color="green.600">
                    {importResult.imported}
                  </Text>
                  <Text fontSize="sm" color="gray.600">
                    Imported
                  </Text>
                </Box>
                {importResult.skipped > 0 && (
                  <Box textAlign="center">
                    <Text fontSize="3xl" fontWeight="bold" color="orange.600">
                      {importResult.skipped}
                    </Text>
                    <Text fontSize="sm" color="gray.600">
                      Skipped
                    </Text>
                  </Box>
                )}
                {importResult.errors > 0 && (
                  <Box textAlign="center">
                    <Text fontSize="3xl" fontWeight="bold" color="red.600">
                      {importResult.errors}
                    </Text>
                    <Text fontSize="sm" color="gray.600">
                      Errors
                    </Text>
                  </Box>
                )}
              </HStack>

              {importResult.error_details && importResult.error_details.length > 0 && (
                <Box>
                  <Text fontWeight="semibold" mb={2}>
                    Error Details
                  </Text>
                  <Box maxH="200px" overflowY="auto" borderWidth={1} borderRadius="md" p={3}>
                    <VStack align="stretch" spacing={2}>
                      {importResult.error_details.map((error, idx) => (
                        <Text key={idx} fontSize="sm" color="red.600">
                          Row {error.row}: {error.error}
                        </Text>
                      ))}
                    </VStack>
                  </Box>
                </Box>
              )}
            </VStack>
          )}
        </ModalBody>

        <ModalFooter>
          <HStack spacing={3}>
            {step !== 'complete' && step !== 'importing' && (
              <Button variant="ghost" onClick={handleClose}>
                Cancel
              </Button>
            )}
            {(step === 'mapping' || step === 'preview') && (
              <Button variant="outline" onClick={handleBack}>
                Back
              </Button>
            )}
            {step === 'upload' && (
              <Button
                colorScheme="blue"
                onClick={handleNext}
                isLoading={previewMutation.isPending}
                isDisabled={!file || !selectedAccountId}
              >
                Preview
              </Button>
            )}
            {step === 'mapping' && (
              <Button
                colorScheme="blue"
                onClick={handleNext}
                isDisabled={!columnMapping.date || !columnMapping.amount}
              >
                Continue
              </Button>
            )}
            {step === 'preview' && (
              <Button colorScheme="blue" onClick={handleNext} isDisabled={importMutation.isPending}>
                Import Transactions
              </Button>
            )}
            {step === 'complete' && (
              <Button colorScheme="blue" onClick={handleClose}>
                Done
              </Button>
            )}
          </HStack>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};
