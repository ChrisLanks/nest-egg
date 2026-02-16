/**
 * Custom Reports page with template management and execution
 */

import {
  Box,
  Container,
  Heading,
  Text,
  VStack,
  HStack,
  Card,
  CardBody,
  Button,
  SimpleGrid,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Badge,
  useToast,
  Spinner,
  Center,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  ModalCloseButton,
  useDisclosure,
  FormControl,
  FormLabel,
  Input,
  Textarea,
  Select,
  IconButton,
} from '@chakra-ui/react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { DeleteIcon, DownloadIcon, ViewIcon } from '@chakra-ui/icons';
import {
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import api from '../services/api';
import { useUserView } from '../contexts/UserViewContext';

interface ReportTemplate {
  id: string;
  name: string;
  description?: string;
  report_type: string;
  config: any;
  is_shared: boolean;
  created_at: string;
  updated_at: string;
}

interface ReportResult {
  data: any[];
  metrics: any;
  dateRange: {
    startDate: string;
    endDate: string;
  };
}

export default function ReportsPage() {
  const { selectedUserId } = useUserView();
  const queryClient = useQueryClient();
  const toast = useToast();
  const { isOpen: isBuilderOpen, onOpen: onBuilderOpen, onClose: onBuilderClose } = useDisclosure();
  const [selectedTemplate, setSelectedTemplate] = useState<ReportTemplate | null>(null);
  const [reportResult, setReportResult] = useState<ReportResult | null>(null);

  // New report form state
  const [newReportName, setNewReportName] = useState('');
  const [newReportDescription, setNewReportDescription] = useState('');
  const [dateRangeType, setDateRangeType] = useState('preset');
  const [preset, setPreset] = useState('last_30_days');
  const [groupBy, setGroupBy] = useState('category');
  const [chartType, setChartType] = useState<'bar' | 'pie' | 'table'>('bar');

  // Fetch templates
  const { data: templates, isLoading: templatesLoading } = useQuery<ReportTemplate[]>({
    queryKey: ['report-templates'],
    queryFn: async () => {
      const response = await api.get('/reports/templates');
      return response.data;
    },
  });

  // Create template mutation
  const createMutation = useMutation({
    mutationFn: async (templateData: any) => {
      const response = await api.post('/reports/templates', templateData);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['report-templates'] });
      toast({ title: 'Report template created', status: 'success', duration: 3000 });
      onBuilderClose();
      resetForm();
    },
    onError: (error: any) => {
      toast({
        title: 'Failed to create template',
        description: error.response?.data?.detail || 'Unknown error',
        status: 'error',
        duration: 5000,
      });
    },
  });

  // Delete template mutation
  const deleteMutation = useMutation({
    mutationFn: async (templateId: string) => {
      await api.delete(`/reports/templates/${templateId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['report-templates'] });
      toast({ title: 'Template deleted', status: 'success', duration: 3000 });
    },
  });

  // Execute report mutation
  const executeMutation = useMutation({
    mutationFn: async (templateId: string) => {
      const params: any = {};
      if (selectedUserId) params.user_id = selectedUserId;

      const response = await api.get(`/reports/templates/${templateId}/execute`, { params });
      return response.data;
    },
    onSuccess: (data) => {
      setReportResult(data);
      toast({ title: 'Report executed', status: 'success', duration: 2000 });
    },
  });

  const resetForm = () => {
    setNewReportName('');
    setNewReportDescription('');
    setDateRangeType('preset');
    setPreset('last_30_days');
    setGroupBy('category');
    setChartType('bar');
  };

  const handleCreateReport = () => {
    if (!newReportName) {
      toast({ title: 'Report name is required', status: 'warning', duration: 3000 });
      return;
    }

    const config = {
      dateRange: {
        type: dateRangeType,
        preset: preset,
      },
      groupBy,
      chartType,
      metrics: ['sum', 'count'],
      sortBy: 'amount',
      sortDirection: 'desc',
      limit: 20,
    };

    createMutation.mutate({
      name: newReportName,
      description: newReportDescription,
      report_type: 'custom',
      config,
      is_shared: false,
    });
  };

  const handleExecuteReport = (template: ReportTemplate) => {
    setSelectedTemplate(template);
    executeMutation.mutate(template.id);
  };

  const handleDownloadReport = async (templateId: string) => {
    try {
      const params: any = {};
      if (selectedUserId) params.user_id = selectedUserId;

      const response = await api.get(`/reports/templates/${templateId}/export`, {
        params,
        responseType: 'blob',
      });

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'report.csv');
      document.body.appendChild(link);
      link.click();
      link.remove();

      toast({ title: 'Report downloaded', status: 'success', duration: 2000 });
    } catch (error) {
      toast({ title: 'Failed to download report', status: 'error', duration: 3000 });
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8', '#82CA9D'];

  if (templatesLoading) {
    return (
      <Container maxW="container.xl" py={8}>
        <Center py={20}>
          <Spinner size="xl" color="brand.500" />
        </Center>
      </Container>
    );
  }

  return (
    <Container maxW="container.xl" py={8}>
      <VStack spacing={8} align="stretch">
        {/* Header */}
        <HStack justify="space-between">
          <Box>
            <Heading size="lg">📊 Custom Reports</Heading>
            <Text color="gray.600">Create and manage custom financial reports</Text>
          </Box>
          <Button colorScheme="blue" onClick={onBuilderOpen}>
            Create New Report
          </Button>
        </HStack>

        {/* Templates List */}
        {templates && templates.length > 0 ? (
          <Card>
            <CardBody>
              <Table variant="simple">
                <Thead>
                  <Tr>
                    <Th>Name</Th>
                    <Th>Description</Th>
                    <Th>Group By</Th>
                    <Th>Date Range</Th>
                    <Th>Shared</Th>
                    <Th>Actions</Th>
                  </Tr>
                </Thead>
                <Tbody>
                  {templates.map((template) => (
                    <Tr key={template.id}>
                      <Td fontWeight="medium">{template.name}</Td>
                      <Td>{template.description || '-'}</Td>
                      <Td>
                        <Badge colorScheme="purple">{template.config.groupBy}</Badge>
                      </Td>
                      <Td fontSize="sm">
                        {template.config.dateRange.type === 'preset'
                          ? template.config.dateRange.preset.replace(/_/g, ' ')
                          : 'Custom range'}
                      </Td>
                      <Td>{template.is_shared ? <Badge colorScheme="green">Shared</Badge> : '-'}</Td>
                      <Td>
                        <HStack spacing={2}>
                          <IconButton
                            aria-label="Execute report"
                            icon={<ViewIcon />}
                            size="sm"
                            colorScheme="blue"
                            onClick={() => handleExecuteReport(template)}
                          />
                          <IconButton
                            aria-label="Download CSV"
                            icon={<DownloadIcon />}
                            size="sm"
                            colorScheme="green"
                            onClick={() => handleDownloadReport(template.id)}
                          />
                          <IconButton
                            aria-label="Delete template"
                            icon={<DeleteIcon />}
                            size="sm"
                            colorScheme="red"
                            variant="ghost"
                            onClick={() => deleteMutation.mutate(template.id)}
                          />
                        </HStack>
                      </Td>
                    </Tr>
                  ))}
                </Tbody>
              </Table>
            </CardBody>
          </Card>
        ) : (
          <Card>
            <CardBody>
              <Center py={10}>
                <VStack spacing={4}>
                  <Text fontSize="lg" color="gray.600">
                    No report templates yet
                  </Text>
                  <Button colorScheme="blue" onClick={onBuilderOpen}>
                    Create Your First Report
                  </Button>
                </VStack>
              </Center>
            </CardBody>
          </Card>
        )}

        {/* Report Results */}
        {reportResult && selectedTemplate && (
          <Card>
            <CardBody>
              <VStack align="stretch" spacing={6}>
                <HStack justify="space-between">
                  <Box>
                    <Heading size="md">{selectedTemplate.name}</Heading>
                    <Text fontSize="sm" color="gray.600">
                      {reportResult.dateRange.startDate} to {reportResult.dateRange.endDate}
                    </Text>
                  </Box>
                  <Button size="sm" onClick={() => setReportResult(null)}>
                    Close
                  </Button>
                </HStack>

                {/* Metrics */}
                {reportResult.metrics && (
                  <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4}>
                    {reportResult.metrics.total_amount !== undefined && (
                      <Card bg="blue.50">
                        <CardBody>
                          <Text fontSize="sm" color="gray.600">
                            Total Amount
                          </Text>
                          <Text fontSize="2xl" fontWeight="bold">
                            {formatCurrency(reportResult.metrics.total_amount)}
                          </Text>
                        </CardBody>
                      </Card>
                    )}
                    {reportResult.metrics.total_transactions !== undefined && (
                      <Card bg="green.50">
                        <CardBody>
                          <Text fontSize="sm" color="gray.600">
                            Transactions
                          </Text>
                          <Text fontSize="2xl" fontWeight="bold">
                            {reportResult.metrics.total_transactions}
                          </Text>
                        </CardBody>
                      </Card>
                    )}
                    {reportResult.metrics.total_items !== undefined && (
                      <Card bg="purple.50">
                        <CardBody>
                          <Text fontSize="sm" color="gray.600">
                            Items
                          </Text>
                          <Text fontSize="2xl" fontWeight="bold">
                            {reportResult.metrics.total_items}
                          </Text>
                        </CardBody>
                      </Card>
                    )}
                  </SimpleGrid>
                )}

                {/* Chart */}
                {selectedTemplate.config.chartType === 'bar' && (
                  <ResponsiveContainer width="100%" height={400}>
                    <BarChart data={reportResult.data}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="name" />
                      <YAxis tickFormatter={(value) => formatCurrency(value)} />
                      <Tooltip formatter={(value: number) => formatCurrency(value)} />
                      <Legend />
                      <Bar dataKey="amount" fill="#3182CE" />
                    </BarChart>
                  </ResponsiveContainer>
                )}

                {selectedTemplate.config.chartType === 'pie' && (
                  <ResponsiveContainer width="100%" height={400}>
                    <PieChart>
                      <Pie
                        data={reportResult.data}
                        cx="50%"
                        cy="50%"
                        labelLine={false}
                        label={(entry) => entry.name}
                        outerRadius={120}
                        fill="#8884d8"
                        dataKey="amount"
                      >
                        {reportResult.data.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip formatter={(value: number) => formatCurrency(value)} />
                    </PieChart>
                  </ResponsiveContainer>
                )}

                {/* Data Table */}
                <Box overflowX="auto">
                  <Table variant="simple" size="sm">
                    <Thead>
                      <Tr>
                        <Th>Name</Th>
                        <Th isNumeric>Amount</Th>
                        {reportResult.data[0]?.count !== undefined && <Th isNumeric>Count</Th>}
                        {reportResult.data[0]?.percentage !== undefined && <Th isNumeric>%</Th>}
                      </Tr>
                    </Thead>
                    <Tbody>
                      {reportResult.data.map((row, index) => (
                        <Tr key={index}>
                          <Td>{row.name}</Td>
                          <Td isNumeric fontWeight="medium">
                            {row.amount !== undefined ? formatCurrency(row.amount) : '-'}
                          </Td>
                          {row.count !== undefined && <Td isNumeric>{row.count}</Td>}
                          {row.percentage !== undefined && (
                            <Td isNumeric>{row.percentage.toFixed(1)}%</Td>
                          )}
                        </Tr>
                      ))}
                    </Tbody>
                  </Table>
                </Box>
              </VStack>
            </CardBody>
          </Card>
        )}
      </VStack>

      {/* Create Report Modal */}
      <Modal isOpen={isBuilderOpen} onClose={onBuilderClose} size="xl">
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Create New Report</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <VStack spacing={4} align="stretch">
              <FormControl isRequired>
                <FormLabel>Report Name</FormLabel>
                <Input
                  placeholder="e.g., Monthly Spending by Category"
                  value={newReportName}
                  onChange={(e) => setNewReportName(e.target.value)}
                />
              </FormControl>

              <FormControl>
                <FormLabel>Description</FormLabel>
                <Textarea
                  placeholder="Optional description"
                  value={newReportDescription}
                  onChange={(e) => setNewReportDescription(e.target.value)}
                  rows={2}
                />
              </FormControl>

              <FormControl isRequired>
                <FormLabel>Date Range</FormLabel>
                <Select value={preset} onChange={(e) => setPreset(e.target.value)}>
                  <option value="last_30_days">Last 30 Days</option>
                  <option value="last_90_days">Last 90 Days</option>
                  <option value="this_month">This Month</option>
                  <option value="this_year">This Year</option>
                  <option value="last_year">Last Year</option>
                </Select>
              </FormControl>

              <FormControl isRequired>
                <FormLabel>Group By</FormLabel>
                <Select value={groupBy} onChange={(e) => setGroupBy(e.target.value)}>
                  <option value="category">Category</option>
                  <option value="merchant">Merchant</option>
                  <option value="account">Account</option>
                  <option value="time">Time Period</option>
                </Select>
              </FormControl>

              <FormControl isRequired>
                <FormLabel>Chart Type</FormLabel>
                <Select
                  value={chartType}
                  onChange={(e) => setChartType(e.target.value as 'bar' | 'pie' | 'table')}
                >
                  <option value="bar">Bar Chart</option>
                  <option value="pie">Pie Chart</option>
                  <option value="table">Table Only</option>
                </Select>
              </FormControl>
            </VStack>
          </ModalBody>
          <ModalFooter>
            <Button variant="ghost" mr={3} onClick={onBuilderClose}>
              Cancel
            </Button>
            <Button
              colorScheme="blue"
              onClick={handleCreateReport}
              isLoading={createMutation.isPending}
            >
              Create Report
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </Container>
  );
}
