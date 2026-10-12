/*
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */
package org.apache.maven.it;

/**
 * Splits Maven IT class names across CI runners. ADR-0027.
 */
final class IntegrationTestShard {

    static final String SHARD_PROPERTY = "maven.it.shard";

    static final String COUNT_PROPERTY = "maven.it.shardCount";

    final Integer shard;

    final int count;

    private IntegrationTestShard(Integer shard, int count) {
        this.shard = shard;
        this.count = count;
    }

    static IntegrationTestShard parse(String shardText, String countText) {
        String shardValue = shardText == null ? "" : shardText.trim();
        String countValue = countText == null ? "" : countText.trim();
        if (shardValue.isEmpty() && countValue.isEmpty()) {
            return new IntegrationTestShard(null, 0);
        }
        if (shardValue.isEmpty() || countValue.isEmpty()) {
            throw new IllegalStateException(SHARD_PROPERTY + " and " + COUNT_PROPERTY + " must both be set");
        }
        int parsedShard;
        int parsedCount;
        try {
            parsedShard = Integer.parseInt(shardValue);
            parsedCount = Integer.parseInt(countValue);
        } catch (NumberFormatException ex) {
            throw new IllegalStateException(SHARD_PROPERTY + " and " + COUNT_PROPERTY + " must be integers", ex);
        }
        if (parsedCount < 1 || parsedShard < 0 || parsedShard >= parsedCount) {
            throw new IllegalStateException(SHARD_PROPERTY + " must be >= 0 and < " + COUNT_PROPERTY);
        }
        return new IntegrationTestShard(parsedShard, parsedCount);
    }

    static int bucket(String className, int count) {
        return Math.floorMod(className.hashCode(), count);
    }

    boolean owns(String className) {
        return shard != null && bucket(className, count) == shard;
    }

    static String className(String uniqueId) {
        int marker = uniqueId.indexOf("[class:");
        if (marker < 0) {
            return null;
        }
        int start = marker + "[class:".length();
        int end = uniqueId.indexOf(']', start);
        if (end < 0) {
            return null;
        }
        return uniqueId.substring(start, end);
    }
}
