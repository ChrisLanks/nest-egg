/**
 * Categories management page with hierarchical support
 */

import {
  Box,
  Container,
  Heading,
  Text,
  VStack,
  HStack,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Spinner,
  Center,
  Button,
  IconButton,
  useToast,
  Input,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalFooter,
  ModalBody,
  ModalCloseButton,
  FormControl,
  FormLabel,
  useDisclosure,
  Select,
} from '@chakra-ui/react';
import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { DeleteIcon, EditIcon, ChevronRightIcon } from '@chakra-ui/icons';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';

interface Category {
  id: string | null;  // null for Plaid categories not yet in DB
  name: string;
  color?: string;
  parent_category_id?: string;
  is_custom: boolean;  // false for Plaid categories
  transaction_count: number;
  created_at?: string;
  updated_at?: string;
}

interface CategoryWithChildren extends Category {
  children?: Category[];
}

export const CategoriesPage = () => {
  const [editingCategory, setEditingCategory] = useState<Category | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    color: '#3B82F6',
    parent_category_id: '',
    plaid_category_name: '',
  });
  const toast = useToast();
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const { isOpen, onOpen, onClose } = useDisclosure();
  const {
    isOpen: isCreateOpen,
    onOpen: onCreateOpen,
    onClose: onCreateClose,
  } = useDisclosure();

  const { data: categories, isLoading } = useQuery({
    queryKey: ['categories'],
    queryFn: async () => {
      const response = await api.get<Category[]>('/categories/');
      return response.data;
    },
  });

  // Organize categories into hierarchical structure (custom categories only)
  const { customCategories, plaidCategories } = useMemo(() => {
    if (!categories) return { customCategories: [], plaidCategories: [] };

    const custom = categories.filter(c => c.is_custom);
    const plaid = categories.filter(c => !c.is_custom);

    const categoryMap = new Map<string, CategoryWithChildren>();
    const roots: CategoryWithChildren[] = [];

    // Create map of all custom categories
    custom.forEach(category => {
      if (category.id) {
        categoryMap.set(category.id, { ...category, children: [] });
      }
    });

    // Build hierarchy for custom categories
    custom.forEach(category => {
      if (!category.id) return;

      const categoryWithChildren = categoryMap.get(category.id)!;
      if (category.parent_category_id) {
        const parent = categoryMap.get(category.parent_category_id);
        if (parent) {
          parent.children!.push(categoryWithChildren);
        } else {
          // Parent doesn't exist, treat as root
          roots.push(categoryWithChildren);
        }
      } else {
        roots.push(categoryWithChildren);
      }
    });

    return { customCategories: roots, plaidCategories: plaid };
  }, [categories]);

  // Get only parent categories for dropdown (custom categories only)
  const parentCategories = useMemo(() => {
    return categories?.filter(c => c.is_custom && !c.parent_category_id) || [];
  }, [categories]);

  const createMutation = useMutation({
    mutationFn: async (data: typeof formData) => {
      const payload = {
        name: data.name,
        color: data.color || null,
        parent_category_id: data.parent_category_id || null,
      };
      const response = await api.post('/categories/', payload);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['categories'] });
      queryClient.invalidateQueries({ queryKey: ['infinite-transactions'] });
      toast({
        title: 'Category created',
        status: 'success',
        duration: 3000,
      });
      onCreateClose();
      resetForm();
    },
    onError: (error: any) => {
      toast({
        title: 'Failed to create category',
        description: error.response?.data?.detail || 'An error occurred',
        status: 'error',
        duration: 5000,
      });
    },
  });

  const updateMutation = useMutation({
    mutationFn: async ({ id, data }: { id: string; data: typeof formData }) => {
      const payload = {
        name: data.name || undefined,
        color: data.color || undefined,
        parent_category_id: data.parent_category_id || null,
      };
      const response = await api.patch(`/categories/${id}`, payload);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['categories'] });
      queryClient.invalidateQueries({ queryKey: ['infinite-transactions'] });
      toast({
        title: 'Category updated',
        status: 'success',
        duration: 3000,
      });
      onClose();
      setEditingCategory(null);
      resetForm();
    },
    onError: (error: any) => {
      toast({
        title: 'Failed to update category',
        description: error.response?.data?.detail || 'An error occurred',
        status: 'error',
        duration: 5000,
      });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (categoryId: string) => {
      await api.delete(`/categories/${categoryId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['categories'] });
      queryClient.invalidateQueries({ queryKey: ['infinite-transactions'] });
      toast({
        title: 'Category deleted',
        status: 'success',
        duration: 3000,
      });
    },
    onError: (error: any) => {
      toast({
        title: 'Failed to delete category',
        description: error.response?.data?.detail || 'Cannot delete category with children or transactions',
        status: 'error',
        duration: 5000,
      });
    },
  });

  const resetForm = () => {
    setFormData({
      name: '',
      color: '#3B82F6',
      parent_category_id: '',
      plaid_category_name: '',
    });
  };

  const handleCreate = () => {
    resetForm();
    onCreateOpen();
  };

  const handleEdit = (category: Category) => {
    if (!category.is_custom) {
      // Converting Plaid category to custom category
      setEditingCategory(null); // No ID yet, will be created
      setFormData({
        name: category.name,
        color: '#3B82F6',
        parent_category_id: '',
        plaid_category_name: category.name, // Link to original Plaid category
      });
      onCreateOpen(); // Use create modal
    } else {
      // Editing existing custom category
      setEditingCategory(category);
      setFormData({
        name: category.name,
        color: category.color || '#3B82F6',
        parent_category_id: category.parent_category_id || '',
        plaid_category_name: '',
      });
      onOpen();
    }
  };

  const handleSubmitCreate = () => {
    if (!formData.name.trim()) {
      toast({
        title: 'Name is required',
        status: 'warning',
        duration: 3000,
      });
      return;
    }
    createMutation.mutate(formData);
  };

  const handleSubmitEdit = () => {
    if (!editingCategory || !formData.name.trim()) {
      toast({
        title: 'Name is required',
        status: 'warning',
        duration: 3000,
      });
      return;
    }
    updateMutation.mutate({ id: editingCategory.id, data: formData });
  };

  const handleDelete = (category: Category) => {
    if (!category.id) {
      toast({
        title: 'Cannot delete Plaid category',
        description: 'Convert it to a custom category first',
        status: 'warning',
        duration: 3000,
      });
      return;
    }

    if (window.confirm(`Are you sure you want to delete "${category.name}"? This will remove it from all transactions.`)) {
      deleteMutation.mutate(category.id);
    }
  };

  const renderCategoryRow = (category: CategoryWithChildren, isChild: boolean = false) => {
    const isPlaid = !category.is_custom;

    return (
      <>
        <Tr key={category.id || category.name} _hover={{ bg: 'gray.50' }}>
          <Td>
            <HStack spacing={2}>
              {isChild && <ChevronRightIcon ml={4} color="gray.400" />}
              <Box
                w={3}
                h={3}
                borderRadius="sm"
                bg={category.color || (isPlaid ? 'gray.300' : 'gray.400')}
              />
              <Text fontWeight={isChild ? 'normal' : 'semibold'}>
                {category.name}
              </Text>
              {isPlaid && (
                <Text fontSize="xs" color="gray.500">
                  (from Plaid)
                </Text>
              )}
            </HStack>
          </Td>
          <Td>
            <Text fontSize="sm" color="gray.600">
              {category.transaction_count} transaction{category.transaction_count !== 1 ? 's' : ''}
            </Text>
          </Td>
          <Td>
            <HStack spacing={2}>
              {isPlaid ? (
                <Button
                  size="sm"
                  colorScheme="blue"
                  variant="ghost"
                  onClick={() => handleEdit(category)}
                >
                  Make Custom
                </Button>
              ) : (
                <>
                  <IconButton
                    icon={<EditIcon />}
                    aria-label="Edit category"
                    size="sm"
                    variant="ghost"
                    onClick={() => handleEdit(category)}
                  />
                  <IconButton
                    icon={<DeleteIcon />}
                    aria-label="Delete category"
                    size="sm"
                    variant="ghost"
                    colorScheme="red"
                    onClick={() => handleDelete(category)}
                    isLoading={deleteMutation.isPending}
                  />
                </>
              )}
            </HStack>
          </Td>
        </Tr>
        {category.children?.map(child => renderCategoryRow(child, true))}
      </>
    );
  };

  if (isLoading) {
    return (
      <Center h="100vh">
        <Spinner size="xl" color="brand.500" />
      </Center>
    );
  }

  return (
    <Container maxW="container.xl" py={8}>
      <VStack spacing={6} align="stretch">
        <HStack justify="space-between" align="start">
          <Box>
            <Heading size="lg">Categories</Heading>
            <Text color="gray.600" mt={2}>
              Manage custom categories with hierarchical organization (max 2 levels). Separate from labels.
            </Text>
          </Box>
          <HStack spacing={2}>
            <Button colorScheme="brand" onClick={handleCreate}>
              Create Category
            </Button>
            <Button variant="ghost" onClick={() => navigate('/transactions')}>
              Back to Transactions
            </Button>
          </HStack>
        </HStack>

        {customCategories.length === 0 && plaidCategories.length === 0 ? (
          <Box
            bg="white"
            p={12}
            borderRadius="lg"
            boxShadow="sm"
            textAlign="center"
          >
            <Text fontSize="lg" color="gray.600" mb={4}>
              No categories yet
            </Text>
            <Text color="gray.500" mb={6}>
              Create categories to organize your transactions
            </Text>
            <Button colorScheme="brand" onClick={handleCreate}>
              Create Your First Category
            </Button>
          </Box>
        ) : (
          <Box bg="white" borderRadius="lg" boxShadow="sm" overflow="hidden">
            <Table variant="simple" size="sm">
              <Thead bg="gray.50">
                <Tr>
                  <Th>Category Name</Th>
                  <Th width="150px">Transactions</Th>
                  <Th width="200px">Actions</Th>
                </Tr>
              </Thead>
              <Tbody>
                {/* Custom Categories (hierarchical) */}
                {customCategories.length > 0 && (
                  <>
                    <Tr bg="gray.100">
                      <Td colSpan={3}>
                        <Text fontWeight="bold" fontSize="sm" color="gray.700">
                          Custom Categories
                        </Text>
                      </Td>
                    </Tr>
                    {customCategories.map(category => renderCategoryRow(category))}
                  </>
                )}

                {/* Plaid Categories (flat) */}
                {plaidCategories.length > 0 && (
                  <>
                    <Tr bg="gray.100">
                      <Td colSpan={3}>
                        <Text fontWeight="bold" fontSize="sm" color="gray.700">
                          Plaid Categories (click "Make Custom" to edit)
                        </Text>
                      </Td>
                    </Tr>
                    {plaidCategories.map(category => renderCategoryRow(category))}
                  </>
                )}
              </Tbody>
            </Table>
          </Box>
        )}
      </VStack>

      {/* Create Modal */}
      <Modal isOpen={isCreateOpen} onClose={onCreateClose}>
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Create New Category</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <VStack spacing={4}>
              <FormControl isRequired>
                <FormLabel>Category Name</FormLabel>
                <Input
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="Enter category name"
                  autoFocus
                />
              </FormControl>

              <FormControl>
                <FormLabel>Parent Category (Optional)</FormLabel>
                <Select
                  value={formData.parent_category_id}
                  onChange={(e) => setFormData({ ...formData, parent_category_id: e.target.value })}
                  placeholder="None (Root level)"
                >
                  {parentCategories.map((category) => (
                    <option key={category.id} value={category.id}>
                      {category.name}
                    </option>
                  ))}
                </Select>
                <Text fontSize="xs" color="gray.500" mt={1}>
                  Categories can only be nested 2 levels deep (parent → child)
                </Text>
              </FormControl>

              <FormControl>
                <FormLabel>Color</FormLabel>
                <Input
                  type="color"
                  value={formData.color}
                  onChange={(e) => setFormData({ ...formData, color: e.target.value })}
                />
              </FormControl>
            </VStack>
          </ModalBody>

          <ModalFooter>
            <Button variant="ghost" mr={3} onClick={onCreateClose}>
              Cancel
            </Button>
            <Button
              colorScheme="brand"
              onClick={handleSubmitCreate}
              isLoading={createMutation.isPending}
            >
              Create
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>

      {/* Edit Modal */}
      <Modal isOpen={isOpen} onClose={onClose}>
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Edit Category</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <VStack spacing={4}>
              <FormControl isRequired>
                <FormLabel>Category Name</FormLabel>
                <Input
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="Enter category name"
                  autoFocus
                />
              </FormControl>

              <FormControl>
                <FormLabel>Parent Category (Optional)</FormLabel>
                <Select
                  value={formData.parent_category_id}
                  onChange={(e) => setFormData({ ...formData, parent_category_id: e.target.value })}
                  placeholder="None (Root level)"
                >
                  {parentCategories
                    .filter(c => c.id !== editingCategory?.id)
                    .map((category) => (
                      <option key={category.id} value={category.id}>
                        {category.name}
                      </option>
                    ))}
                </Select>
                <Text fontSize="xs" color="gray.500" mt={1}>
                  Cannot make this a child if it already has children
                </Text>
              </FormControl>

              <FormControl>
                <FormLabel>Color</FormLabel>
                <Input
                  type="color"
                  value={formData.color}
                  onChange={(e) => setFormData({ ...formData, color: e.target.value })}
                />
              </FormControl>
            </VStack>
          </ModalBody>

          <ModalFooter>
            <Button variant="ghost" mr={3} onClick={onClose}>
              Cancel
            </Button>
            <Button
              colorScheme="brand"
              onClick={handleSubmitEdit}
              isLoading={updateMutation.isPending}
            >
              Save Changes
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </Container>
  );
};
