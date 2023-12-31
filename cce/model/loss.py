
######################
### Imports
######################

## External
import torch

######################
### Functions
######################

def compute_entity_loss(model,
                        entity_weights,
                        entity_logits,
                        inputs,
                        reduce=True):
    """

    """
    ## Entity Order
    entity_order = model.get_entities()
    ## Loss Cache
    total_loss = 0 if reduce else []
    ## Iterate Through Entities
    for e, (entity, logits) in enumerate(zip(entity_order, entity_logits)):
        if model._use_crf:
            eloss = model.entity_crf[e](emissions=logits,
                                        tags=inputs["entity_labels"][:,e,:],
                                        mask=inputs["attention_mask"]==1,
                                        reduction="token_mean")
            eloss = - eloss
        else:
            ## Loss Function
            ent_weight = entity_weights[entity] if entity_weights is not None else None
            ent_loss_fcn = torch.nn.CrossEntropyLoss(weight=ent_weight)
            ## Flatten
            labels_ravel = inputs["entity_labels"][:,e,:].ravel()
            mask_ravel = (inputs["attention_mask"]==1).ravel()
            logits_ravel = logits.flatten(0,1)
            ## Update Total Loss
            eloss = ent_loss_fcn(logits_ravel[mask_ravel],
                                 labels_ravel[mask_ravel])
        ## Update Cache
        if reduce:
            total_loss += eloss
        else:
            total_loss.append(eloss)
    ## Return
    return total_loss

def compute_attribute_loss(model,
                           attribute_weights,
                           attribute_logits,
                           inputs,
                           reduce=True):
    """

    """
    ## Get Attribute Order
    attribute_order = model.get_attributes()
    ## Loss Cache
    total_loss = 0 if reduce else []
    ## Iterate Through
    for a, (attribute, logits) in enumerate(zip(attribute_order, attribute_logits)):
        ## Skip if No Attribute in Batch
        if logits is None:
            if not reduce:
                total_loss.append(torch.nan)
            continue
        ## Loss Function
        at_weight = attribute_weights[attribute] if attribute_weights is not None else None
        at_loss_fcn = torch.nn.CrossEntropyLoss(weight=at_weight)
        ## Computation
        at_lbls = inputs["attribute_spans"][attribute]["metadata"][:,-1]
        ## Reduction
        if reduce:
            at_loss = at_loss_fcn(logits, at_lbls)
            total_loss += at_loss
        else:
            ## Get Entities
            at_entities = model._encoder_attributes[attribute].get_tasks()
            at_ents = inputs["attribute_spans"][attribute]["metadata"][:,0]
            ## Initialize Per Entity cache
            at_loss = torch.zeros((len(at_entities), 2), dtype=float)
            ## Iterate Through Entities
            for e, ent in enumerate(at_entities):
                ent_mask = (at_ents == e)
                if ent_mask.any():
                    at_loss[e,0] = at_loss_fcn(logits[ent_mask], at_lbls[ent_mask])
                    at_loss[e,1] = ent_mask.sum().item()
            ## Cache Loss
            total_loss.append(at_loss)
    ## Return
    return total_loss