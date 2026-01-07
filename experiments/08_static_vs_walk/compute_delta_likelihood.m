function prob_delta = compute_delta_likelihood(Delta, current_point, trans_train, neighbors)
    % Compute P(Delta | location=current_point) by marginalizing over possible origins
    % P(Δ | j) = Σᵢ P(Δ | came_from_i, now_at_j) · P(came_from_i | j)
    
    prob_delta = 0;
    neighbor_list = neighbors{current_point};  % Possible previous locations
    
    if isempty(neighbor_list)
        prob_delta = 1;  % Shouldn't happen, but handle gracefully
        return;
    end
    
    for prev_point = neighbor_list
        % Find transition distribution for prev_point → current_point
        trans_idx = -1;
        for k = 1:length(trans_train)
            if trans_train(k).from == prev_point && trans_train(k).to == current_point
                trans_idx = k;
                break;
            end
        end
        
        if trans_idx > 0 && trans_train(trans_idx).std_delta < inf
            mu = trans_train(trans_idx).mean_delta;
            sigma = trans_train(trans_idx).std_delta;
            
            if sigma > 0
                % P(Delta | came from prev_point)
                prob_this_transition = normpdf(Delta, mu, sigma);
            else
                % Degenerate case
                prob_this_transition = (Delta == mu);
            end
            
            % Assume uniform prior over neighbors
            prior = 1 / length(neighbor_list);
            
            prob_delta = prob_delta + prob_this_transition * prior;
        else
            % No training data for this transition - use weak prior
            prob_delta = prob_delta + 1e-6 / length(neighbor_list);
        end
    end
    
    % Normalize (prevent numerical issues)
    if prob_delta == 0
        prob_delta = 1e-10;
    end
end
