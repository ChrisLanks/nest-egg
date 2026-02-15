/**
 * Main modal for adding accounts with multi-step wizard
 */

import { useState } from 'react';
import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalCloseButton,
  useToast,
} from '@chakra-ui/react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../../../services/api';
import { formatAccountType } from '../../../utils/formatAccountType';
import { SourceSelectionStep, type AccountSource } from './SourceSelectionStep';
import { ManualAccountTypeStep } from './ManualAccountTypeStep';
import { BasicManualAccountForm } from './forms/BasicManualAccountForm';
import { InvestmentAccountForm } from './forms/InvestmentAccountForm';
import { PropertyAccountForm } from './forms/PropertyAccountForm';
import { VehicleAccountForm } from './forms/VehicleAccountForm';
import { PlaidLinkStep } from './PlaidLinkStep';
import type {
  BasicManualAccountFormData,
  InvestmentAccountFormData,
  PropertyAccountFormData,
  VehicleAccountFormData,
  AccountType,
} from '../schemas/manualAccountSchemas';

type WizardStep =
  | 'source_selection'
  | 'plaid_link'
  | 'mx_link'
  | 'manual_type_selection'
  | 'manual_form_basic'
  | 'manual_form_investment'
  | 'manual_form_property'
  | 'manual_form_vehicle'
  | 'success';

interface AddAccountModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const AddAccountModal = ({ isOpen, onClose }: AddAccountModalProps) => {
  const [currentStep, setCurrentStep] = useState<WizardStep>('source_selection');
  const [_selectedSource, setSelectedSource] = useState<AccountSource | null>(null);
  const [selectedAccountType, setSelectedAccountType] = useState<AccountType | null>(null);
  const [_selectedCategory, setSelectedCategory] = useState<'basic' | 'investment' | 'alternative' | 'insurance' | 'securities' | 'business' | 'property' | null>(null);

  const toast = useToast();
  const queryClient = useQueryClient();

  // Reset state when modal closes
  const handleClose = () => {
    setCurrentStep('source_selection');
    setSelectedSource(null);
    setSelectedAccountType(null);
    setSelectedCategory(null);
    onClose();
  };

  // Handle source selection
  const handleSelectSource = (source: AccountSource) => {
    setSelectedSource(source);

    if (source === 'plaid') {
      setCurrentStep('plaid_link');
    } else if (source === 'mx') {
      setCurrentStep('mx_link');
    } else if (source === 'manual') {
      setCurrentStep('manual_type_selection');
    }
  };

  // Handle manual account type selection
  const handleSelectAccountType = (type: AccountType, category: 'basic' | 'investment' | 'alternative' | 'insurance' | 'securities' | 'business' | 'property') => {
    setSelectedAccountType(type);
    setSelectedCategory(category);

    if (category === 'basic') {
      setCurrentStep('manual_form_basic');
    } else if (category === 'investment' || category === 'alternative' || category === 'securities' || category === 'insurance' || category === 'business') {
      // All investment-related categories use the investment form
      setCurrentStep('manual_form_investment');
    } else if (category === 'property') {
      if (type === 'property') {
        setCurrentStep('manual_form_property');
      } else if (type === 'vehicle') {
        setCurrentStep('manual_form_vehicle');
      }
    }
  };

  // Back handlers
  const handleBackToSourceSelection = () => {
    setCurrentStep('source_selection');
    setSelectedSource(null);
  };

  const handleBackToTypeSelection = () => {
    setCurrentStep('manual_type_selection');
    setSelectedAccountType(null);
    setSelectedCategory(null);
  };

  // Handle Plaid success
  const handlePlaidSuccess = () => {
    queryClient.invalidateQueries({ queryKey: ['accounts'] });
    handleClose();
  };

  // Create manual account mutation
  const createManualAccountMutation = useMutation({
    mutationFn: async (data: BasicManualAccountFormData | InvestmentAccountFormData | PropertyAccountFormData | VehicleAccountFormData) => {
      const response = await api.post('/accounts/manual', {
        ...data,
        account_source: 'manual',
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['accounts'] });
      toast({
        title: 'Account created',
        description: 'Your account has been added successfully.',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
      handleClose();
    },
    onError: (error: any) => {
      // Handle validation errors (array) or simple error messages (string)
      let errorMessage = 'An error occurred while creating the account.';
      if (error.response?.data?.detail) {
        if (Array.isArray(error.response.data.detail)) {
          // Validation errors - extract messages
          errorMessage = error.response.data.detail.map((err: any) => err.msg).join(', ');
        } else if (typeof error.response.data.detail === 'string') {
          errorMessage = error.response.data.detail;
        }
      }

      toast({
        title: 'Error creating account',
        description: errorMessage,
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    },
  });

  // Handle manual account form submissions
  const handleBasicManualAccountSubmit = (data: BasicManualAccountFormData) => {
    createManualAccountMutation.mutate(data);
  };

  const handleInvestmentAccountSubmit = (data: InvestmentAccountFormData) => {
    // Calculate total balance from holdings
    const balance = data.holdings.reduce((sum, holding) => {
      return sum + (holding.shares * holding.price_per_share);
    }, 0);

    createManualAccountMutation.mutate({
      ...data,
      balance,
    } as any);
  };

  const handlePropertyAccountSubmit = (data: PropertyAccountFormData) => {
    createManualAccountMutation.mutate({
      name: data.name,
      account_type: 'property' as any,
      property_type: data.property_classification as any,  // Map classification to backend property_type
      balance: data.value,
      institution: data.address,
    } as any);
  };

  const handleVehicleAccountSubmit = (data: VehicleAccountFormData) => {
    createManualAccountMutation.mutate({
      name: data.name,
      account_type: 'vehicle' as any,
      balance: data.value,
      institution: `${data.year} ${data.make} ${data.model}`,
      account_number_last4: data.mileage?.toString() || undefined,
    } as any);
  };

  // Get modal title based on current step
  const getModalTitle = () => {
    switch (currentStep) {
      case 'source_selection':
        return 'Add Account';
      case 'manual_type_selection':
        return 'Select Account Type';
      case 'manual_form_basic':
      case 'manual_form_investment':
      case 'manual_form_property':
      case 'manual_form_vehicle':
        return selectedAccountType ? `Add ${formatAccountType(selectedAccountType)} Account` : 'Account Details';
      case 'plaid_link':
        return 'Connect Bank Account';
      case 'mx_link':
        return 'Connect via MX';
      case 'success':
        return 'Success';
      default:
        return 'Add Account';
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={handleClose} size="2xl">
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>{getModalTitle()}</ModalHeader>
        <ModalCloseButton />
        <ModalBody pb={6}>
          {/* Step 1: Source Selection */}
          {currentStep === 'source_selection' && (
            <SourceSelectionStep onSelectSource={handleSelectSource} />
          )}

          {/* Step 2: Manual Account Type Selection */}
          {currentStep === 'manual_type_selection' && (
            <ManualAccountTypeStep
              onSelectType={handleSelectAccountType}
              onBack={handleBackToSourceSelection}
            />
          )}

          {/* Step 3: Basic Manual Account Form */}
          {currentStep === 'manual_form_basic' && selectedAccountType && (
            <BasicManualAccountForm
              defaultAccountType={selectedAccountType}
              onSubmit={handleBasicManualAccountSubmit}
              onBack={handleBackToTypeSelection}
              isLoading={createManualAccountMutation.isPending}
            />
          )}

          {/* Plaid Link */}
          {currentStep === 'plaid_link' && (
            <PlaidLinkStep
              onSuccess={handlePlaidSuccess}
              onBack={handleBackToSourceSelection}
            />
          )}

          {/* Placeholder for MX Link */}
          {currentStep === 'mx_link' && (
            <div>
              <p>MX integration will be implemented in Phase 5.</p>
              <button onClick={handleBackToSourceSelection}>Back</button>
            </div>
          )}

          {/* Investment Account Form */}
          {currentStep === 'manual_form_investment' && selectedAccountType && (
            <InvestmentAccountForm
              defaultAccountType={selectedAccountType}
              onSubmit={handleInvestmentAccountSubmit}
              onBack={handleBackToTypeSelection}
              isLoading={createManualAccountMutation.isPending}
            />
          )}

          {/* Property Account Form */}
          {currentStep === 'manual_form_property' && (
            <PropertyAccountForm
              onSubmit={handlePropertyAccountSubmit}
              onBack={handleBackToTypeSelection}
              isLoading={createManualAccountMutation.isPending}
            />
          )}

          {/* Vehicle Account Form */}
          {currentStep === 'manual_form_vehicle' && (
            <VehicleAccountForm
              onSubmit={handleVehicleAccountSubmit}
              onBack={handleBackToTypeSelection}
              isLoading={createManualAccountMutation.isPending}
            />
          )}
        </ModalBody>
      </ModalContent>
    </Modal>
  );
};
