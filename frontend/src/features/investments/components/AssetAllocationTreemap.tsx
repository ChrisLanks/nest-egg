/**
 * Interactive treemap for asset allocation with drill-down capability
 */

import { Box, Heading, HStack, Button, Text } from '@chakra-ui/react';
import { useState } from 'react';
import { Treemap, ResponsiveContainer } from 'recharts';

interface TreemapNode {
  name: string;
  value: number;
  percent: number;
  children?: TreemapNode[];
  color?: string;
  [key: string]: any; // Index signature for Recharts compatibility
}

interface AssetAllocationTreemapProps {
  data: TreemapNode;
  onDrillDown?: (node: TreemapNode | null) => void;
}

const COLORS = {
  stocks: '#4299E1', // blue
  bonds: '#48BB78', // green
  realEstate: '#ED8936', // orange
  crypto: '#9F7AEA', // purple
  cash: '#38B2AC', // teal
  other: '#A0AEC0', // gray
  domestic: '#3182CE',
  international: '#805AD5',
  etf: '#319795',
  mutualFund: '#D69E2E',
};

export const AssetAllocationTreemap = ({ data, onDrillDown }: AssetAllocationTreemapProps) => {
  const [breadcrumbs, setBreadcrumbs] = useState<TreemapNode[]>([]);
  const [currentNode, setCurrentNode] = useState<TreemapNode>(data);

  const handleClick = (node: any) => {
    if (node.children && node.children.length > 0) {
      setBreadcrumbs([...breadcrumbs, currentNode]);
      setCurrentNode(node);
      onDrillDown?.(node);
    }
  };

  const handleBreadcrumbClick = (index: number) => {
    if (index === -1) {
      // Go back to root
      setCurrentNode(data);
      setBreadcrumbs([]);
      onDrillDown?.(null);
    } else {
      // Go back to specific level
      const newNode = breadcrumbs[index];
      setCurrentNode(newNode);
      setBreadcrumbs(breadcrumbs.slice(0, index));
      onDrillDown?.(newNode);
    }
  };

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  const CustomizedContent = (props: any) => {
    const { x, y, width, height, name, value, percent, fill, children, color } = props;

    // Only show label if box is large enough
    const showLabel = width > 60 && height > 40;
    const showPercent = width > 80 && height > 50;

    // Calculate percent if not provided (shouldn't happen, but safety check)
    const displayPercent = percent || 0;

    return (
      <g>
        <rect
          x={x}
          y={y}
          width={width}
          height={height}
          style={{
            fill: color || fill,
            stroke: '#fff',
            strokeWidth: 2,
            cursor: children ? 'pointer' : 'default',
          }}
          onClick={() => children && handleClick(props)}
        />
        {showLabel && name && (
          <g>
            <text
              x={x + width / 2}
              y={y + height / 2 - (showPercent ? 8 : 0)}
              textAnchor="middle"
              fill="#fff"
              fontSize={width > 100 ? 14 : 11}
              fontWeight="bold"
            >
              {name}
            </text>
            {showPercent && (
              <>
                <text
                  x={x + width / 2}
                  y={y + height / 2 + 6}
                  textAnchor="middle"
                  fill="#fff"
                  fontSize={11}
                >
                  {formatCurrency(value)}
                </text>
                <text
                  x={x + width / 2}
                  y={y + height / 2 + 20}
                  textAnchor="middle"
                  fill="#fff"
                  fontSize={10}
                >
                  {Number(displayPercent).toFixed(1)}%
                </text>
              </>
            )}
          </g>
        )}
      </g>
    );
  };

  return (
    <Box>
      {/* Breadcrumb Navigation */}
      {breadcrumbs.length > 0 && (
        <HStack mb={4} spacing={2}>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => handleBreadcrumbClick(-1)}
          >
            All Assets
          </Button>
          {breadcrumbs.map((crumb, index) => (
            <HStack key={index} spacing={2}>
              <Text color="gray.500">/</Text>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => handleBreadcrumbClick(index)}
              >
                {crumb.name}
              </Button>
            </HStack>
          ))}
          {currentNode !== data && (
            <>
              <Text color="gray.500">/</Text>
              <Text fontWeight="bold">{currentNode.name}</Text>
            </>
          )}
        </HStack>
      )}

      {/* Current Level Title */}
      <Heading size="md" mb={4}>
        {currentNode.name} - {formatCurrency(currentNode.value)}
      </Heading>

      {/* Treemap */}
      <ResponsiveContainer width="100%" height={400}>
        {currentNode.children && currentNode.children.length > 0 ? (
          <Treemap
            data={currentNode.children}
            dataKey="value"
            stroke="#fff"
            fill="#8884d8"
            content={<CustomizedContent />}
          />
        ) : (
          <Text fontSize="sm" color="gray.600" textAlign="center" py={8}>
            No data to display
          </Text>
        )}
      </ResponsiveContainer>

      {/* Help Text */}
      {currentNode.children && currentNode.children.length > 0 && (
        <Text fontSize="sm" color="gray.600" mt={2}>
          Click on a category to drill down
        </Text>
      )}
    </Box>
  );
};
