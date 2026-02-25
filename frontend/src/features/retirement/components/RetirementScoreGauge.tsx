/**
 * Semicircular gauge showing retirement readiness score (0-100).
 * Color: red (<40), orange (40-59), yellow (60-79), green (80+).
 */

import { Box, Text, useColorModeValue, VStack } from '@chakra-ui/react';

interface RetirementScoreGaugeProps {
  score: number | null;
  successRate?: number | null;
  isLoading?: boolean;
}

function getScoreColor(score: number): string {
  if (score >= 80) return '#48BB78'; // green
  if (score >= 60) return '#ECC94B'; // yellow
  if (score >= 40) return '#ED8936'; // orange
  return '#F56565'; // red
}

function getScoreLabel(score: number): string {
  if (score >= 80) return 'On Track';
  if (score >= 60) return 'Needs Attention';
  if (score >= 40) return 'At Risk';
  return 'Behind';
}

export function RetirementScoreGauge({ score, successRate, isLoading }: RetirementScoreGaugeProps) {
  const bgColor = useColorModeValue('white', 'gray.800');
  const textColor = useColorModeValue('gray.600', 'gray.400');
  const trackColor = useColorModeValue('#E2E8F0', '#2D3748');

  if (isLoading || score === null) {
    return (
      <Box bg={bgColor} p={6} borderRadius="xl" textAlign="center" shadow="sm">
        <VStack spacing={2}>
          <Text fontSize="lg" color={textColor}>
            {isLoading ? 'Calculating...' : 'Run a simulation to see your readiness score'}
          </Text>
        </VStack>
      </Box>
    );
  }

  const color = getScoreColor(score);
  const label = getScoreLabel(score);

  // SVG arc gauge
  const size = 200;
  const strokeWidth = 16;
  const radius = (size - strokeWidth) / 2;
  const cx = size / 2;
  const cy = size / 2 + 10;

  // Arc from 180 to 0 degrees (semicircle, left to right)
  const startAngle = Math.PI;
  const endAngle = 0;
  const scoreAngle = startAngle - (score / 100) * Math.PI;

  const x1 = cx + radius * Math.cos(startAngle);
  const y1 = cy - radius * Math.sin(startAngle);
  const x2 = cx + radius * Math.cos(endAngle);
  const y2 = cy - radius * Math.sin(endAngle);
  const xScore = cx + radius * Math.cos(scoreAngle);
  const yScore = cy - radius * Math.sin(scoreAngle);

  const largeArc = score > 50 ? 1 : 0;

  const trackPath = `M ${x1} ${y1} A ${radius} ${radius} 0 1 1 ${x2} ${y2}`;
  const scorePath = `M ${x1} ${y1} A ${radius} ${radius} 0 ${largeArc} 1 ${xScore} ${yScore}`;

  return (
    <Box bg={bgColor} p={6} borderRadius="xl" textAlign="center" shadow="sm">
      <VStack spacing={1}>
        <svg width={size} height={size / 2 + 30} viewBox={`0 0 ${size} ${size / 2 + 30}`}>
          {/* Track */}
          <path
            d={trackPath}
            fill="none"
            stroke={trackColor}
            strokeWidth={strokeWidth}
            strokeLinecap="round"
          />
          {/* Score arc */}
          {score > 0 && (
            <path
              d={scorePath}
              fill="none"
              stroke={color}
              strokeWidth={strokeWidth}
              strokeLinecap="round"
            />
          )}
          {/* Score number */}
          <text
            x={cx}
            y={cy - 10}
            textAnchor="middle"
            fontSize="42"
            fontWeight="bold"
            fill={color}
          >
            {score}
          </text>
          <text
            x={cx}
            y={cy + 16}
            textAnchor="middle"
            fontSize="14"
            fill={textColor}
          >
            {label}
          </text>
        </svg>
        <Text fontSize="xl" fontWeight="bold" color={textColor}>
          Retirement Readiness
        </Text>
        {successRate !== null && successRate !== undefined && (
          <Text fontSize="sm" color={textColor}>
            {successRate.toFixed(0)}% chance of not running out of money
          </Text>
        )}
      </VStack>
    </Box>
  );
}
